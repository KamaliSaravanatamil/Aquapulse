import 'package:flutter_test/flutter_test.dart';

import 'package:iot_dashboard/main.dart';

void main() {
  testWidgets('renders the AquaPulse dashboard', (WidgetTester tester) async {
    await tester.pumpWidget(const AquaPulseApp());

    expect(find.text('AquaPulse Dashboard'), findsOneWidget);
    expect(find.text('Water Quality Dashboard'), findsOneWidget);
    expect(find.textContaining('Connect your ESP32 sensor'), findsOneWidget);
  });
}
