import 'package:flutter/material.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'services/config_service.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final TextEditingController _ipController = TextEditingController();
  final ConfigService _configService = ConfigService();
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _ipController.text = _configService.serverIp;
  }

  @override
  void dispose() {
    _ipController.dispose();
    super.dispose();
  }

  Future<void> _saveSettings() async {
    setState(() => _isLoading = true);
    await _configService.setServerIp(_ipController.text.trim());

    // Notify Background Service to Reconnect
    FlutterBackgroundService()
        .invoke('update_ip', {'ip': _ipController.text.trim()});

    setState(() => _isLoading = false);

    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Saved! Please restart app or reconnect.')),
      );
      Navigator.pop(context, true); // Return true to indicate change
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Settings"),
      ),
      body: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            const Text(
              "Configure Server IP",
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            const Text(
              "Enter the IP address shown on the Server Console (e.g. 192.168.1.5:8000)",
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 20),
            TextField(
              controller: _ipController,
              decoration: const InputDecoration(
                labelText: "Server IP",
                hintText: "192.168.x.x:port",
                border: OutlineInputBorder(),
                prefixIcon: Icon(Icons.computer),
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              height: 50,
              child: ElevatedButton(
                onPressed: _isLoading ? null : _saveSettings,
                child: _isLoading
                    ? const CircularProgressIndicator()
                    : const Text("SAVE CONFIGURATION"),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
