from pathlib import Path

# Keep the upstream EKA2L1 Android startup intact. Previous custom launcher
# patches replaced MainActivity/EmulatorActivity startup and caused native
# crashes before the emulator created its game surface.
gradle = Path('eka2l1/src/emu/android/app/build.gradle')
strings = Path('eka2l1/src/emu/android/app/src/main/res/values/strings.xml')

if gradle.exists():
    text = gradle.read_text()
    text = text.replace('applicationId "com.github.eka2l1"', 'applicationId "com.devilhandle.snakeex"')
    gradle.write_text(text)

if strings.exists():
    text = strings.read_text()
    text = text.replace('<string name="app_name" translatable="false">EKA2L1</string>', '<string name="app_name" translatable="false">Snake EX</string>')
    strings.write_text(text)

print('Snake EX patch: identity only; upstream EKA2L1 startup preserved.')
