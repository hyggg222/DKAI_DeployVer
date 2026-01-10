class VehicleRecord {
  final int? id;
  final String plate;
  final String? carImageUrl;  // Nullable
  final String? plateImageUrl; // Nullable
  final DateTime timestamp;

  VehicleRecord({
    this.id,
    required this.plate,
    this.carImageUrl,
    this.plateImageUrl,
    required this.timestamp,
  });

  factory VehicleRecord.fromJson(Map<String, dynamic> json) {
    return VehicleRecord(
      id: json['id'],
      plate: json['plate'] ?? 'UNKNOWN',
      carImageUrl: json['image_url'], // Can be null
      plateImageUrl: json['plate_image_url'], // Can be null
      timestamp: DateTime.parse(json['timestamp']),
    );
  }
}
