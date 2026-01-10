import 'services/config_service.dart';

class AppConstants {
  // Dynamic via ConfigService
  static String get serverIp => ConfigService().serverIp;
  
  static String get baseUrl => ConfigService().baseUrl;
  static String get socketUrl => ConfigService().socketUrl;
  
  // API Endpoints
  static String get historyApi => "$baseUrl/api/data/history";
  
  // To get images from MinIO via Nginx Proxy
  static String getImageUrl(String partialPath) {
    if (partialPath.startsWith('http')) return partialPath;
    // Nginx handles /parking-images/... and proxies to MinIO
    return "$baseUrl$partialPath";
  }
}
