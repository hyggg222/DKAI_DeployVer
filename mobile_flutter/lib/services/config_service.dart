import 'package:shared_preferences/shared_preferences.dart';

class ConfigService {
  static final ConfigService _instance = ConfigService._internal();

  factory ConfigService() {
    return _instance;
  }

  ConfigService._internal();

  static const String _kIpKey = 'server_ip';
  static const String _kDefaultIp = '10.0.2.2:8001'; // Default for Emulator

  late SharedPreferences _prefs;
  String _serverIp = _kDefaultIp;

  String get serverIp => _serverIp;

  // Computed properties
  String get baseUrl => "http://$_serverIp";
  String get socketUrl => "http://$_serverIp";

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    _serverIp = _prefs.getString(_kIpKey) ?? _kDefaultIp;
  }

  Future<void> setServerIp(String ip) async {
    _serverIp = ip;
    await _prefs.setString(_kIpKey, ip);
  }
}
