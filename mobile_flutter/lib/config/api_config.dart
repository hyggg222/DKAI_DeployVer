/// API Configuration for DK_AI Mobile App
///
/// Update the IP address below to match your server's IP address.
/// You can find your server IP by running 'ipconfig' (Windows) or 'ifconfig' (Mac/Linux)
class ApiConfig {
  // Server Configuration
  // IMPORTANT: Replace '192.168.1.100' with your actual server IP address
  // The server will display its IP address when it starts
  static const String serverIp = '192.168.1.100';
  static const String serverPort = '8000';

  // Base URLs
  static const String baseUrl = 'http://$serverIp:$serverPort';
  static const String wsUrl = 'ws://$serverIp:$serverPort';

  // API Endpoints
  static const String logsEndpoint = '$baseUrl/api/history';
  static const String statusEndpoint = '$baseUrl/api/status';

  // WebSocket Events
  static const String vehicleDetectedEvent = 'notify_vehicle';
  static const String plateRecognizedEvent =
      'vehicle_event'; // Using 'notify_vehicle' mainly

  // Timeout Settings
  static const Duration connectionTimeout = Duration(seconds: 10);
  static const Duration receiveTimeout = Duration(seconds: 30);

  // Development Mode
  // Set to true to enable debug logging
  static const bool isDevelopment = true;

  /// Returns the full server URL
  static String get fullUrl => baseUrl;

  /// Returns the WebSocket URL
  static String get socketUrl => wsUrl;

  /// Check if server is configured
  static bool get isConfigured {
    return serverIp != '192.168.1.100' && serverIp.isNotEmpty;
  }
}
