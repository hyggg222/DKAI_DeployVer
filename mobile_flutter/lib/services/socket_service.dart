import 'dart:developer';
import 'package:socket_io_client/socket_io_client.dart' as IO;
import '../consts.dart';

class SocketService {
  // 1. Đổi 'late IO.Socket' thành 'IO.Socket?' (Có thể null)
  IO.Socket? socket;

  void connect({required Function(Map<String, dynamic>) onVehicleDetected}) {
    // 2. Khởi tạo socket
    socket = IO.io(AppConstants.socketUrl, 
      IO.OptionBuilder()
        .setTransports(['polling', 'websocket']) 
        .setPath('/socket.io')
        .disableAutoConnect() // Tắt tự kết nối để mình tự gọi connect() bên dưới
        .setReconnectionAttempts(5)
        .build()
    );

    // 3. Dùng dấu ?. để gọi hàm an toàn (nếu socket null thì không gọi)
    socket?.onConnect((_) {
      log('✅ Connected to Socket.io server');
    });

    socket?.on('notify_vehicle', (data) {
      log('📩 New vehicle detected: $data');
      if (data != null) {
        onVehicleDetected(Map<String, dynamic>.from(data));
      }
    });

    socket?.onDisconnect((_) => log('❌ Disconnected'));
    socket?.onConnectError((err) => log('⚠️ Connection Error: $err'));

    // 4. Bắt đầu kết nối
    socket?.connect();
  }

  void dispose() {
    // 5. Kiểm tra null trước khi ngắt kết nối
    socket?.dispose();
    socket = null; // Xóa sạch biến
  }
}