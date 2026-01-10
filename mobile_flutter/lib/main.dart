import 'dart:async';
import 'dart:convert'; // Added for ArchiveScreen
import 'dart:typed_data';
import 'dart:math';
import 'dart:ui'; // For DartPluginRegistrant
import 'dart:io'; // For Platform check

import 'package:flutter/material.dart';
import 'package:flutter/services.dart'; // Added for SystemChrome
import 'package:http/http.dart' as http;
import 'package:image/image.dart' as img;
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:permission_handler/permission_handler.dart';

import 'services/config_service.dart';
import 'settings_screen.dart';

// ============================================================================
// 1. CONFIGURATION & THEME
// ============================================================================

const Color kColorPrimaryDark = Color(0xFF0D1E4C);
const Color kColorPrimaryMedium = Color(0xFF22577E);
const Color kColorBackground = Color(0xFFF5F9FC);
const Color kColorSuccess = Color(0xFF28a745);
const Color kColorTextDark = Color(0xFF1A1A1A);

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Set Status Bar Color to match App Bar
  SystemChrome.setSystemUIOverlayStyle(const SystemUiOverlayStyle(
    statusBarColor: kColorPrimaryDark,
    statusBarIconBrightness: Brightness.light,
  ));

  await ConfigService().init();
  await initializeService(); // START BACKGROUND SERVICE
  runApp(const DKApp());
}

// ============================================================================
// 2. BACKGROUND SERVICE LOGIC
// ============================================================================

Future<void> initializeService() async {
  final service = FlutterBackgroundService();

  const AndroidNotificationChannel channel = AndroidNotificationChannel(
    'dkai_service_persistent', // New ID to force update
    'DKAI Background Service', // name
    description: 'Maintains connection to server', // description
    importance: Importance.low, // silent
    showBadge: false, // NO DOT on app icon
    playSound: false,
  );

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();

  if (Platform.isIOS || Platform.isAndroid) {
    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);
  }

  await service.configure(
    androidConfiguration: AndroidConfiguration(
      onStart: onStart,
      autoStart: false,
      isForegroundMode: true,
      notificationChannelId: 'dkai_service_persistent', // Match new ID
      initialNotificationTitle: 'DKAI MONITOR',
      initialNotificationContent: 'System Ready',
      foregroundServiceNotificationId: 888,
    ),
    iosConfiguration: IosConfiguration(
      autoStart: false,
      onForeground: onStart,
      onBackground: onIosBackground,
    ),
  );

  // Start immediately to ensure connection
  service.startService();
}

@pragma('vm:entry-point')
Future<bool> onIosBackground(ServiceInstance service) async {
  return true;
}

@pragma('vm:entry-point')
void onStart(ServiceInstance service) async {
  DartPluginRegistrant.ensureInitialized();

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();

  // Init Notification Plugin IN ISOLATE
  const AndroidInitializationSettings initializationSettingsAndroid =
      AndroidInitializationSettings('@mipmap/ic_launcher');
  const InitializationSettings initializationSettings =
      InitializationSettings(android: initializationSettingsAndroid);
  await flutterLocalNotificationsPlugin.initialize(initializationSettings);

  // SOCKET LOGIC
  // We hardcode the fallback URL or try to read config if accessible.
  // For robustness in this standalone setup, we assume the user configured IP is correct
  // but since we are in isolate, we might just assume the default or passed value.
  // 1. Initialize Config Service (Background Isolate)
  final configService = ConfigService();
  await configService.init(); // Read from SharedPreferences
  String socketUrl = "http://${configService.serverIp}";
  print("BG: Initializing Socket with URL: $socketUrl");

  // Connect Socket FIRST so it is available for listeners
  IO.Socket socket = IO.io(socketUrl, <String, dynamic>{
    'transports': ['websocket'],
    'path': '/socket.io',
    'autoConnect': true,
    'reconnection': true,
  });

  // Listen for Stop
  service.on('stopService').listen((event) {
    service.stopSelf();
  });

  // Listen for Session Clear Request from UI
  service.on('clear_server_session').listen((event) {
    print("BG: Requesting Server to Clear Session...");
    socket.emit('clear_session', {});
  });

  // Listen for IP UPDATE from UI
  service.on('update_ip').listen((event) {
    if (event != null && event['ip'] != null) {
      final newIp = event['ip'];
      print("BG: Updating IP to $newIp and Reconnecting...");
      socketUrl = "http://$newIp";

      // Reconnec Logic
      socket.disconnect();
      socket.dispose();
      socket = IO.io(socketUrl, <String, dynamic>{
        'transports': ['websocket'],
        'path': '/socket.io',
        'autoConnect': true,
        'reconnection': true,
      });
      _bindSocketEvents(socket, service, flutterLocalNotificationsPlugin);
      socket.connect();
    }
  });

  _bindSocketEvents(socket, service, flutterLocalNotificationsPlugin);
  socket.connect();
}

void _bindSocketEvents(IO.Socket socket, ServiceInstance service,
    FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin) {
  socket.onConnect((_) {
    service.invoke('status', {'status': 'connected'});
    print(
        "Background Socket Connected to ${socket.io.options?['hostname'] ?? 'Unknown'}");
  });

  socket.onDisconnect((_) {
    print("Background Socket Disconnected");
  });

  socket.on('notify_vehicle', (data) async {
    print("BG: New Vehicle: ${data['plate']}");

    // SHOW NOTIFICATION (High Priority)
    const AndroidNotificationDetails androidPlatformChannelSpecifics =
        AndroidNotificationDetails('dkai_alerts', 'DKAI Alerts',
            channelDescription: 'Vehicle Detection',
            importance: Importance.max,
            priority: Priority.high,
            showWhen: true,
            fullScreenIntent: true);

    const NotificationDetails platformChannelSpecifics =
        NotificationDetails(android: androidPlatformChannelSpecifics);

    await flutterLocalNotificationsPlugin.show(0, 'Xe Mới: ${data['plate']}',
        'Nhấn để xem chi tiết', platformChannelSpecifics);

    // Send to UI
    service.invoke('notify_vehicle', data);
  });

  socket.connect();
}

// ============================================================================
// 3. DATA MODEL
// ============================================================================

class VehicleRecord {
  String plateNumber;
  final DateTime timestamp;
  Uint8List? carImageBytes;
  Uint8List? plateImageBytes;

  // New fields for URL-based images
  String? carImageUrl;
  String? plateImageUrl;

  // Status tracking
  bool isCarConfirmed = false;
  bool isPlateConfirmed = false;

  VehicleRecord({
    required this.plateNumber,
    required this.timestamp,
    this.carImageBytes,
    this.plateImageBytes,
    this.carImageUrl,
    this.plateImageUrl,
  });

  // Factory for simulation data
  factory VehicleRecord.simulate() {
    return VehicleRecord(
      plateNumber: "30H-${10000 + Random().nextInt(89999)}",
      timestamp: DateTime.now(),
      carImageBytes: null,
      plateImageBytes: null,
    );
  }

  factory VehicleRecord.fromJson(Map<String, dynamic> json) {
    return VehicleRecord(
      plateNumber: json['plate'] ?? "UNKNOWN",
      timestamp: json['timestamp'] != null
          ? DateTime.parse(json['timestamp'])
          : DateTime.now(),
      carImageUrl: json['image_url'],
      plateImageUrl: json['plate_image_url'],
    );
  }
}

// ============================================================================
// 4. MAIN APP WIDGET
// ============================================================================

class DKApp extends StatelessWidget {
  const DKApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'DKAI',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        scaffoldBackgroundColor: kColorBackground,
        primaryColor: kColorPrimaryDark,
        colorScheme: ColorScheme.fromSeed(seedColor: kColorPrimaryDark),
        useMaterial3: true,
        fontFamily: 'Roboto',
      ),
      home: const IntroScreen(),
    );
  }
}

// ============================================================================
// 5. SCREEN 1: INTRO SCREEN
// ============================================================================

class IntroScreen extends StatefulWidget {
  const IntroScreen({super.key});

  @override
  State<IntroScreen> createState() => _IntroScreenState();
}

class _IntroScreenState extends State<IntroScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _scaleAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(begin: 1.0, end: 1.1).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );

    _checkSession();
  }

  Future<void> _checkSession() async {
    final prefs = await SharedPreferences.getInstance();
    final bool hasStarted = prefs.getBool('has_started') ?? false;
    if (hasStarted && mounted) {
      _navigateToMain();
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _navigateToMain() async {
    // Save Session State
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('has_started', true);

    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      MaterialPageRoute(builder: (_) => const MainScreen()),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: kColorPrimaryDark,
      body: Center(
        child: SafeArea(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Text(
                "DKAI MONITOR",
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 32,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 2.0,
                ),
              ),
              const SizedBox(height: 20),
              // SETTINGS BUTTON
              TextButton.icon(
                  onPressed: () {
                    Navigator.of(context).push(MaterialPageRoute(
                        builder: (_) => const SettingsScreen()));
                  },
                  icon: const Icon(Icons.settings, color: Colors.white70),
                  label: const Text("Cấu hình IP",
                      style: TextStyle(color: Colors.white70))),
              const SizedBox(height: 60),
              AnimatedBuilder(
                animation: _scaleAnimation,
                builder: (context, child) {
                  return Transform.scale(
                    scale: _scaleAnimation.value,
                    child: child,
                  );
                },
                child: GestureDetector(
                  onTap: _navigateToMain,
                  child: Container(
                    width: 160,
                    height: 160,
                    decoration: BoxDecoration(
                      color: kColorPrimaryMedium,
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: Colors.white.withOpacity(0.3),
                          blurRadius: 20,
                          spreadRadius: 5,
                        )
                      ],
                    ),
                    alignment: Alignment.center,
                    child: const Text(
                      "START",
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

// ============================================================================
// 6. SCREEN 2: MAIN SCREEN
// ============================================================================

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();
  final List<VehicleRecord> _queue = [];
  Timer? _simulationTimer;
  Timer? _midnightTimer;

  // UI State
  final TextEditingController _plateController = TextEditingController();
  bool _isProcessing = false;

  @override
  void initState() {
    super.initState();
    _requestPermission();
    _initServiceListeners();
    _scheduleMidnightReset();
  }

  Future<void> _requestPermission() async {
    await Permission.notification.request();
  }

  void _initServiceListeners() async {
    final service = FlutterBackgroundService();
    bool isRunning = await service.isRunning();
    if (!isRunning) service.startService(); // Ensure it's running

    // Listen for data from Background Service
    service.on('notify_vehicle').listen((event) {
      if (event != null && mounted) {
        print("UI: Received from Service: $event");

        setState(() {
          final newVehicle = VehicleRecord.fromJson(event);
          _queue.add(newVehicle);
          if (_queue.length == 1) _loadVehicle(_queue.first);
        });

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
              content: Text("Xe mới: ${event['plate']}"),
              duration: const Duration(seconds: 2)),
        );
      }
    });
  }

  void _scheduleMidnightReset() {
    final now = DateTime.now();
    final midnight = DateTime(now.year, now.month, now.day + 1);
    final duration = midnight.difference(now);

    print(
        "Scheduled midnight reset in: ${duration.inHours}h ${duration.inMinutes % 60}m");

    _midnightTimer?.cancel();
    _midnightTimer = Timer(duration, () {
      if (mounted) _stopAndExit();
    });
  }

  Future<void> _stopAndExit() async {
    // 1. Clear Local State
    setState(() {
      _queue.clear();
      _plateController.clear();
      _isProcessing = false;
    });

    // 2. Stop Background Service
    final service = FlutterBackgroundService();
    // Send signal to background service to tell SERVER to clear session
    service.invoke("clear_server_session");

    // Give it a moment to send
    await Future.delayed(const Duration(milliseconds: 300));

    service.invoke("stopService");

    // 3. Reset Session Flag
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('has_started', false);

    // 4. Exit App (Cleanest way to ensure no state lingers)
    if (mounted) {
      SystemNavigator.pop();
    }
  }

  @override
  void dispose() {
    _simulationTimer?.cancel();
    _midnightTimer?.cancel();
    _plateController.dispose();
    super.dispose();
  }

  // --- LOGIC ---

  void _loadVehicle(VehicleRecord vehicle) {
    _plateController.text = vehicle.plateNumber;
  }

  void _openImageModal(bool isCar) {
    if (_queue.isEmpty) return;

    final vehicle = _queue.first;
    final currentBytes =
        isCar ? vehicle.carImageBytes : vehicle.plateImageBytes;
    final currentUrl = isCar ? vehicle.carImageUrl : vehicle.plateImageUrl;

    showDialog(
      context: context,
      barrierColor: Colors.black.withOpacity(0.8),
      builder: (ctx) => ImageEditorModal(
        initialImage: currentBytes,
        initialUrl: currentUrl,
        title: isCar ? "ẢNH XE" : "ẢNH BIỂN SỐ",
        onConfirm: (Uint8List? newBytes) {
          setState(() {
            if (isCar) {
              vehicle.carImageBytes = newBytes;
              vehicle.isCarConfirmed = true;
            } else {
              vehicle.plateImageBytes = newBytes;
              vehicle.isPlateConfirmed = true;
            }
          });
        },
      ),
    );
  }

  Future<void> _processAndUpload() async {
    if (_queue.isEmpty) return;
    final vehicle = _queue.first;

    setState(() => _isProcessing = true);

    try {
      // Prepare Request
      final String baseUrl = ConfigService().baseUrl;
      var request = http.MultipartRequest(
          'POST', Uri.parse('$baseUrl/api/ingest/confirm'));
      request.fields['plate'] = _plateController.text;
      request.fields['timestamp'] = vehicle.timestamp.toString();

      // 1. Car Image
      if (vehicle.carImageBytes != null) {
        request.files.add(http.MultipartFile.fromBytes(
            'image', vehicle.carImageBytes!,
            filename: 'car_confirmed.jpg'));
      } else if (vehicle.carImageUrl != null) {
        // Download from URL and attach
        try {
          // Handle localhost url logic if needed, but assuming standard http here
          final String baseUrl = ConfigService().baseUrl;
          Uri uri = Uri.parse(vehicle.carImageUrl!.startsWith('http')
              ? vehicle.carImageUrl!
              : "$baseUrl${vehicle.carImageUrl!}");
          final resp = await http.get(uri);
          if (resp.statusCode == 200) {
            request.files.add(http.MultipartFile.fromBytes(
                'image', resp.bodyBytes,
                filename: 'car_confirmed.jpg'));
          }
        } catch (e) {
          print("Failed to download car image: $e");
        }
      }

      // 2. Plate Image
      if (vehicle.plateImageBytes != null) {
        request.files.add(http.MultipartFile.fromBytes(
            'plate_image', vehicle.plateImageBytes!,
            filename: 'plate_confirmed.jpg'));
      } else if (vehicle.plateImageUrl != null) {
        try {
          final String baseUrl = ConfigService().baseUrl;
          Uri uri = Uri.parse(vehicle.plateImageUrl!.startsWith('http')
              ? vehicle.plateImageUrl!
              : "$baseUrl${vehicle.plateImageUrl!}");
          final resp = await http.get(uri);
          if (resp.statusCode == 200) {
            request.files.add(http.MultipartFile.fromBytes(
                'plate_image', resp.bodyBytes,
                filename: 'plate_confirmed.jpg'));
          }
        } catch (e) {
          print("Failed to download plate image: $e");
        }
      }

      print("Sending confirm request...");
      final response = await request.send();

      if (response.statusCode == 200) {
        _onUploadSuccess();
      } else {
        final respStr = await response.stream.bytesToString();
        _showError("Server Error: ${response.statusCode}\n$respStr");
      }
    } catch (e) {
      _showError("Error processing: $e");
    } finally {
      setState(() => _isProcessing = false);
    }
  }

  void _onUploadSuccess() {
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
          content: Text('Processing & Upload Successful!'),
          backgroundColor: kColorSuccess),
    );

    setState(() {
      _queue.removeAt(0);
      if (_queue.isNotEmpty) {
        _loadVehicle(_queue.first);
      }
    });
  }

  void _showError(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(msg), backgroundColor: Colors.red),
    );
  }

  // --- UI BUILDING ---

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      key: _scaffoldKey,
      drawer: _buildDrawer(),
      backgroundColor: kColorBackground,
      body: Center(
        child: SafeArea(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: Column(
              children: [
                _buildHeader(),
                Expanded(
                  child: _queue.isEmpty
                      ? _buildEmptyState()
                      : _buildDashboard(_queue.first),
                ),
                _buildFooter(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Container(
      height: 60,
      color: kColorPrimaryDark,
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          // MENU BUTTON
          IconButton(
            icon: const Icon(Icons.menu, color: Colors.white, size: 28),
            onPressed: () {
              _scaffoldKey.currentState?.openDrawer();
            },
          ),
          const SizedBox(width: 8),
          const Text(
            "DKAI MONITOR",
            style: TextStyle(
                color: Colors.white,
                fontSize: 20,
                fontWeight: FontWeight.bold,
                letterSpacing: 1.2),
          ),
          const Spacer(),
          // Queue Counter
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: Colors.red,
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              "${_queue.length}",
              style: const TextStyle(
                  color: Colors.white, fontWeight: FontWeight.bold),
            ),
          )
        ],
      ),
    );
  }

  Widget _buildDrawer() {
    return Drawer(
      width: MediaQuery.of(context).size.width * 0.85,
      child: Container(
        color: kColorBackground,
        child: SafeArea(
          child: Column(
            children: [
              // Header
              Container(
                height: 120,
                width: double.infinity,
                color: kColorPrimaryDark,
                alignment: Alignment.bottomLeft,
                padding: const EdgeInsets.all(20),
                child: const Text("MENU",
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 30,
                        fontWeight: FontWeight.bold)),
              ),

              Expanded(
                child: ListView(
                  padding: const EdgeInsets.all(20),
                  children: [
                    // 1. STOP BUTTON
                    _buildDrawerItem(
                        label: "NGỪNG PHIÊN",
                        icon: Icons.power_settings_new,
                        color: Colors.red,
                        onTap: () async {
                          // Confirm Dialog
                          final confirm = await showDialog<bool>(
                              context: context,
                              builder: (ctx) => AlertDialog(
                                    title: const Text("Xác nhận"),
                                    content: const Text(
                                        "Bạn có chắc chắn muốn ngừng phiên làm việc?"),
                                    actions: [
                                      TextButton(
                                          onPressed: () =>
                                              Navigator.pop(ctx, false),
                                          child: const Text("Hủy")),
                                      ElevatedButton(
                                        style: ElevatedButton.styleFrom(
                                            backgroundColor: Colors.red),
                                        onPressed: () =>
                                            Navigator.pop(ctx, true),
                                        child: const Text("Ngừng",
                                            style:
                                                TextStyle(color: Colors.white)),
                                      )
                                    ],
                                  ));

                          if (confirm == true) {
                            Navigator.pop(context); // Close Drawer
                            _stopAndExit();
                          }
                        }),
                    const SizedBox(height: 16),

                    // 2. ARCHIVE BUTTON
                    _buildDrawerItem(
                        label: "KHO LƯU TRỮ",
                        icon: Icons.folder_special,
                        color: kColorPrimaryMedium,
                        onTap: () {
                          Navigator.pop(context); // Close Drawer
                          Navigator.of(context).push(MaterialPageRoute(
                              builder: (_) => const ArchiveScreen()));
                        }),
                  ],
                ),
              ),

              const Padding(
                padding: EdgeInsets.all(16.0),
                child: Text("DKAI v1.0", style: TextStyle(color: Colors.grey)),
              )
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildDrawerItem({
    required String label,
    required IconData icon,
    required Color color,
    required VoidCallback onTap,
  }) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(12),
            boxShadow: [
              BoxShadow(
                  color: Colors.black.withOpacity(0.05),
                  blurRadius: 10,
                  offset: const Offset(0, 4))
            ]),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(12),
              decoration: BoxDecoration(
                color: color.withOpacity(0.1),
                shape: BoxShape.circle,
              ),
              child: Icon(icon, color: color, size: 28),
            ),
            const SizedBox(width: 20),
            Text(
              label,
              style: TextStyle(
                color: kColorTextDark,
                fontWeight: FontWeight.bold,
                fontSize: 18,
              ),
            ),
            const Spacer(),
            const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey)
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyState() {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.folder_off, size: 80, color: Colors.grey[400]),
          const SizedBox(height: 16),
          Text(
            "Hồ Sơ Trống",
            style: TextStyle(fontSize: 18, color: Colors.grey[600]),
          ),
          const SizedBox(height: 8),
          const Text(
            "Đang chờ tín hiệu từ AI Agent...",
            style: TextStyle(fontSize: 14, color: Colors.grey),
          ),
        ],
      ),
    );
  }

  Widget _buildDashboard(VehicleRecord vehicle) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: kColorPrimaryMedium.withOpacity(0.1),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.access_time,
                    color: kColorPrimaryMedium, size: 20),
                const SizedBox(width: 8),
                Text(
                  DateFormat('HH:mm - dd/MM/yyyy').format(vehicle.timestamp),
                  style: const TextStyle(
                      color: kColorPrimaryMedium,
                      fontWeight: FontWeight.bold,
                      fontSize: 16),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // ACTION BUTTONS
          _buildLargeActionButton(
            label: "ẢNH XE",
            icon: Icons.directions_car,
            isConfirmed: vehicle.isCarConfirmed,
            hasImage:
                vehicle.carImageBytes != null || vehicle.carImageUrl != null,
            onTap: () => _openImageModal(true),
          ),
          const SizedBox(height: 16),
          _buildLargeActionButton(
            label: "ẢNH BIỂN SỐ",
            icon: Icons.camera_alt,
            isConfirmed: vehicle.isPlateConfirmed,
            hasImage: vehicle.plateImageBytes != null ||
                vehicle.plateImageUrl != null,
            onTap: () => _openImageModal(false),
          ),

          const SizedBox(height: 32),

          // Plate Input
          const Text("Biển Số Xe",
              style: TextStyle(color: Colors.grey, fontSize: 14)),
          const SizedBox(height: 8),
          Container(
            height: 80,
            decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.grey.shade300),
                boxShadow: [
                  BoxShadow(
                      color: Colors.black.withOpacity(0.05),
                      blurRadius: 10,
                      offset: const Offset(0, 4))
                ]),
            alignment: Alignment.center,
            child: TextField(
              controller: _plateController,
              textAlign: TextAlign.center,
              style: const TextStyle(
                fontSize: 40,
                fontWeight: FontWeight.bold,
                color: kColorPrimaryDark,
              ),
              decoration: const InputDecoration(
                border: InputBorder.none,
                hintText: "NO-PLATE",
                hintStyle: TextStyle(color: Colors.black12),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildLargeActionButton({
    required String label,
    required IconData icon,
    required bool isConfirmed,
    required bool hasImage,
    required VoidCallback onTap,
  }) {
    Color bgColor = hasImage ? kColorPrimaryMedium : Colors.grey.shade400;

    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 120, // Large height
        padding: const EdgeInsets.symmetric(horizontal: 24),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: bgColor.withOpacity(0.4),
              blurRadius: 8,
              offset: const Offset(0, 4),
            )
          ],
        ),
        child: Row(
          children: [
            Icon(icon, color: Colors.white, size: 40),
            const SizedBox(width: 24),
            Text(
              label,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.bold,
              ),
            ),
            const Spacer(),
            if (isConfirmed)
              Container(
                padding: const EdgeInsets.all(4),
                decoration: const BoxDecoration(
                  color: Colors.white,
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.check, color: kColorSuccess, size: 32),
              )
          ],
        ),
      ),
    );
  }

  Widget _buildFooter() {
    bool canSubmit = false;
    if (_queue.isNotEmpty) {
      canSubmit = true;
    }

    return Container(
      padding: const EdgeInsets.all(16),
      color: Colors.white,
      child: SizedBox(
        height: 56,
        width: double.infinity,
        child: ElevatedButton(
          onPressed: (canSubmit && !_isProcessing) ? _processAndUpload : null,
          style: ElevatedButton.styleFrom(
            backgroundColor: kColorPrimaryDark,
            disabledBackgroundColor: Colors.grey.shade300,
            shape:
                RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
          ),
          child: _isProcessing
              ? const SizedBox(
                  width: 24,
                  height: 24,
                  child: CircularProgressIndicator(
                      color: Colors.white, strokeWidth: 2))
              : const Text(
                  "XÁC NHẬN",
                  style: TextStyle(
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                      color: Colors.white),
                ),
        ),
      ),
    );
  }
}

// ============================================================================
// 7. IMAGE EDITOR MODAL
// ============================================================================

class ImageEditorModal extends StatefulWidget {
  final Uint8List? initialImage;
  final String? initialUrl; // New
  final String title;
  final Function(Uint8List?) onConfirm;

  const ImageEditorModal({
    super.key,
    required this.initialImage,
    this.initialUrl,
    required this.title,
    required this.onConfirm,
  });

  @override
  State<ImageEditorModal> createState() => _ImageEditorModalState();
}

class _ImageEditorModalState extends State<ImageEditorModal> {
  Uint8List? _currentImage;
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _currentImage = widget.initialImage;
  }

  Future<void> _pickImage(ImageSource source) async {
    try {
      final XFile? picked = await _picker.pickImage(source: source);
      if (picked != null) {
        final bytes = await picked.readAsBytes();
        setState(() {
          _currentImage = bytes;
        });
      }
    } catch (e) {
      debugPrint("Error picking image: $e");
    }
  }

  @override
  Widget build(BuildContext context) {
    return BackdropFilter(
      filter: ImageFilter.blur(sigmaX: 5.0, sigmaY: 5.0),
      child: Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: EdgeInsets.zero,
        child: SizedBox(
          width: double.infinity,
          height: double.infinity,
          child: Column(
            children: [
              // HEADER
              Padding(
                padding: const EdgeInsets.only(top: 40, right: 20),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.close,
                          color: Colors.white, size: 32),
                      onPressed: () => Navigator.of(context).pop(),
                    )
                  ],
                ),
              ),

              // MAIN IMAGE AREA
              Expanded(
                child: Center(
                  child: Container(
                    margin: const EdgeInsets.all(16),
                    // Keep 4:3 Aspect Ratio
                    width: 600,
                    child: AspectRatio(
                      aspectRatio: 4 / 3,
                      child: Container(
                        decoration: BoxDecoration(
                          color: Colors.black,
                          border: Border.all(color: Colors.white, width: 2),
                        ),
                        child: _buildImageContent(),
                      ),
                    ),
                  ),
                ),
              ),

              // ACTION BAR
              Container(
                color: Colors.white,
                padding: const EdgeInsets.all(20),
                child: Row(
                  children: [
                    // EDIT BUTTON
                    Expanded(
                      flex: 1,
                      child: SizedBox(
                        height: 50,
                        child: OutlinedButton.icon(
                          onPressed: () {
                            // Show generic picker selection
                            showModalBottomSheet(
                                context: context,
                                builder: (_) => Wrap(
                                      children: [
                                        ListTile(
                                            leading:
                                                const Icon(Icons.camera_alt),
                                            title: const Text('Chụp ảnh'),
                                            onTap: () {
                                              Navigator.pop(context);
                                              _pickImage(ImageSource.camera);
                                            }),
                                        ListTile(
                                            leading:
                                                const Icon(Icons.photo_library),
                                            title: const Text('Thư viện'),
                                            onTap: () {
                                              Navigator.pop(context);
                                              _pickImage(ImageSource.gallery);
                                            }),
                                      ],
                                    ));
                          },
                          icon:
                              const Icon(Icons.edit, color: kColorPrimaryDark),
                          label: const Text("SỬA",
                              style: TextStyle(
                                  color: kColorPrimaryDark,
                                  fontWeight: FontWeight.bold)),
                          style: OutlinedButton.styleFrom(
                            side: const BorderSide(
                                color: kColorPrimaryDark, width: 2),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    // CONFIRM BUTTON
                    Expanded(
                      flex: 2,
                      child: SizedBox(
                        height: 50,
                        child: ElevatedButton.icon(
                          onPressed: (_currentImage == null &&
                                  widget.initialUrl == null)
                              ? null
                              : () {
                                  widget.onConfirm(_currentImage);
                                  Navigator.of(context).pop();
                                },
                          icon: const Icon(Icons.check, color: Colors.white),
                          label: const Text("XÁC NHẬN",
                              style: TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.bold)),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: kColorSuccess,
                            disabledBackgroundColor: Colors.grey,
                          ),
                        ),
                      ),
                    ),
                  ],
                ),
              )
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildImageContent() {
    if (_currentImage != null) {
      return Image.memory(_currentImage!, fit: BoxFit.contain);
    }
    if (widget.initialUrl != null && widget.initialUrl!.isNotEmpty) {
      // Append localhost to URL if it's relative
      String url = widget.initialUrl!;
      if (!url.startsWith('http')) {
        // Assume configured base url or just leave relative if handled by image network?
        // Let's use config service logic or assume absolute for robustness
        // But for display inside helper, we just try to render
      }
      return Image.network(
        url,
        fit: BoxFit.contain,
        errorBuilder: (ctx, _, __) => const Center(
            child: Text("Load Error", style: TextStyle(color: Colors.white))),
      );
    }
    return const Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Icon(Icons.image_not_supported, color: Colors.white54, size: 50),
        Text("Chưa có ảnh", style: TextStyle(color: Colors.white54))
      ],
    );
  }
}

// ============================================================================
// 8. ARCHIVE SCREEN ("KHO LƯU TRỮ")
// ============================================================================

class ArchiveScreen extends StatefulWidget {
  const ArchiveScreen({super.key});

  @override
  State<ArchiveScreen> createState() => _ArchiveScreenState();
}

class _ArchiveScreenState extends State<ArchiveScreen> {
  List<dynamic> _history = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _fetchHistory();
  }

  Future<void> _fetchHistory() async {
    try {
      final String baseUrl = ConfigService().baseUrl;
      final uri = Uri.parse('$baseUrl/api/ingest/history');
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(utf8.decode(response.bodyBytes));
        setState(() {
          _history = data;
          _isLoading = false;
        });
      } else {
        debugPrint("History Error: ${response.statusCode}");
        setState(() => _isLoading = false);
      }
    } catch (e) {
      debugPrint("Fetch History Error: $e");
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("KHO LƯU TRỮ",
            style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white)),
        backgroundColor: kColorPrimaryDark,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => Navigator.of(context).pop(),
        ),
      ),
      backgroundColor: kColorBackground,
      body: SafeArea(
        child: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _history.isEmpty
                ? const Center(
                    child: Text("Chưa có hồ sơ nào được lưu.",
                        style: TextStyle(color: Colors.grey)))
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: _history.length,
                    itemBuilder: (context, index) {
                      final item = _history[index];
                      return _buildHistoryCard(item);
                    },
                  ),
      ),
    );
  }

  Widget _buildHistoryCard(dynamic item) {
    final plate = item['plate'] ?? "UNKNOWN";
    final count = item['count'] ?? 1;
    final folderName = item['folder_name'] ?? "${plate}_$count";
    final timestamp = item['timestamp'] ?? "";

    return Card(
      elevation: 2,
      margin: const EdgeInsets.only(bottom: 12),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        leading: Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: kColorPrimaryMedium.withOpacity(0.1),
            shape: BoxShape.circle,
          ),
          child: const Icon(Icons.folder, color: kColorPrimaryMedium),
        ),
        title: Text(
          folderName,
          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
        ),
        subtitle: Text(
          timestamp,
          style: const TextStyle(color: Colors.grey, fontSize: 12),
        ),
        trailing:
            const Icon(Icons.arrow_forward_ios, size: 16, color: Colors.grey),
        onTap: () => _showDetail(item),
      ),
    );
  }

  void _showDetail(dynamic item) {
    // Construct URLs manually properly
    final String baseUrl = ConfigService().baseUrl;
    final String folderName = item['folder_name'];
    final String carImgPath = item['car_image'];
    final String plateImgPath = item['plate_image'];

    // We mounted 'outputs' to '/storage'
    final String carUrl = "$baseUrl/storage/$folderName/$carImgPath";
    final String plateUrl = "$baseUrl/storage/$folderName/$plateImgPath";
    final String plateNum = item['plate'];

    showDialog(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        insetPadding: EdgeInsets.zero,
        child: Container(
          width: double.infinity,
          height: double.infinity,
          color: Colors.black.withOpacity(0.9),
          child: Stack(
            children: [
              // Close Button
              Positioned(
                top: 40,
                right: 20,
                child: IconButton(
                  icon: const Icon(Icons.close, color: Colors.white, size: 30),
                  onPressed: () => Navigator.of(ctx).pop(),
                ),
              ),

              Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    const Text(
                      "CHI TIẾT HỒ SƠ",
                      style: TextStyle(
                          color: Colors.white,
                          fontSize: 20,
                          fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 20),

                    // CAR IMAGE
                    Expanded(
                      flex: 4,
                      child: Container(
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.white24),
                        ),
                        child: Image.network(
                          carUrl,
                          fit: BoxFit.contain,
                          errorBuilder: (_, __, ___) => const Center(
                              child: Icon(Icons.broken_image,
                                  color: Colors.white)),
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),

                    // PLATE IMAGE
                    Expanded(
                      flex: 2,
                      child: Row(
                        children: [
                          Expanded(
                            child: Container(
                              decoration: BoxDecoration(
                                border: Border.all(color: Colors.white24),
                              ),
                              child: Image.network(
                                plateUrl,
                                fit: BoxFit.contain,
                                errorBuilder: (_, __, ___) => const Center(
                                    child: Icon(Icons.broken_image,
                                        color: Colors.white)),
                              ),
                            ),
                          ),
                          const SizedBox(width: 10),
                          // INFO
                          Expanded(
                            child: Column(
                              mainAxisAlignment: MainAxisAlignment.center,
                              children: [
                                const Text("Biển Số:",
                                    style: TextStyle(color: Colors.grey)),
                                const SizedBox(height: 4),
                                Text(
                                  plateNum,
                                  style: const TextStyle(
                                      color: kColorSuccess,
                                      fontSize: 24,
                                      fontWeight: FontWeight.bold),
                                ),
                              ],
                            ),
                          )
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
