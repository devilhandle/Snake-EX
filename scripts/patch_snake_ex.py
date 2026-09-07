from pathlib import Path

root = Path('eka2l1/src/emu/android/app/src/main/java/com/github/eka2l1')
main = root / 'MainActivity.java'
text = main.read_text()
text = text.replace('import android.os.Bundle;\n', 'import android.os.Bundle;\nimport java.io.File;\nimport java.io.IOException;\n')

old = '''    private void showAppList() {
        Emulator.initializeFolders();
        setVolumeControlStream(AudioManager.STREAM_MUSIC);
        AppsListFragment appsListFragment = new AppsListFragment();
        FragmentManager fragmentManager = getSupportFragmentManager();
        fragmentManager.beginTransaction()
                .replace(R.id.container, appsListFragment).commitNowAllowingStateLoss();
    }
'''
new = '''    private void showAppList() {
        setVolumeControlStream(AudioManager.STREAM_MUSIC);
        launchSnakeEx();
    }

    private void launchSnakeEx() {
        new Thread(() -> {
            try {
                Emulator.initializeForShortcutLaunch(this);
                File gameDir = new File(getFilesDir(), "snakeex");
                if (!gameDir.exists() && !gameDir.mkdirs()) throw new IOException("Cannot create game directory");
                File romFile = new File(gameDir, "nokia6600.rom");
                File sisFile = new File(gameDir, "Snake EX-2.sis");
                copyAssetIfNeeded("snakeex/nokia6600.rom", romFile);
                copyAssetIfNeeded("snakeex/Snake EX-2.sis", sisFile);

                if (Emulator.getDevices().length == 0) {
                    int result = Emulator.installDevice("", romFile.getAbsolutePath(), false);
                    if (result != Emulator.INSTALL_DEVICE_ERROR_NONE) throw new IOException("Nokia 6600 ROM install failed: " + result);
                }

                long snakeUid = -1;
                String snakeName = "Snake EX";
                String[] apps = Emulator.getInstalledAppsRaw();
                for (int i = 0; i + 1 < apps.length; i += 2) {
                    String name = apps[i + 1];
                    if (name != null && name.toLowerCase().contains("snake")) {
                        snakeUid = Long.parseLong(apps[i]);
                        snakeName = name;
                        break;
                    }
                }

                if (snakeUid < 0) {
                    int result = Emulator.installApp(sisFile.getAbsolutePath());
                    if (result != 0) throw new IOException("Snake EX SIS install failed: " + result);
                    apps = Emulator.getInstalledAppsRaw();
                    for (int i = 0; i + 1 < apps.length; i += 2) {
                        String name = apps[i + 1];
                        if (name != null && name.toLowerCase().contains("snake")) {
                            snakeUid = Long.parseLong(apps[i]);
                            snakeName = name;
                            break;
                        }
                    }
                }

                if (snakeUid < 0) throw new IOException("Snake EX application UID was not found after installation");

                final long uid = snakeUid;
                final String name = snakeName;
                runOnUiThread(() -> {
                    Intent intent = new Intent(this, com.github.eka2l1.emu.EmulatorActivity.class);
                    intent.putExtra(com.github.eka2l1.emu.Constants.KEY_APP_UID, uid);
                    intent.putExtra(com.github.eka2l1.emu.Constants.KEY_APP_NAME, name);
                    intent.putExtra(com.github.eka2l1.emu.Constants.KEY_APP_IS_SHORTCUT, true);
                    startActivity(intent);
                    finish();
                });
            } catch (Exception e) {
                e.printStackTrace();
                runOnUiThread(() -> new AlertDialog.Builder(this)
                        .setTitle("Snake EX")
                        .setMessage("Oyun başlatılamadı: " + e.getMessage())
                        .setCancelable(false)
                        .setPositiveButton(android.R.string.ok, (d, w) -> finish())
                        .show());
            }
        }, "snake-ex-bootstrap").start();
    }

    private void copyAssetIfNeeded(String assetPath, File destination) throws IOException {
        if (destination.exists() && destination.length() > 0) return;
        try (java.io.InputStream in = getAssets().open(assetPath);
             java.io.FileOutputStream out = new java.io.FileOutputStream(destination)) {
            byte[] buffer = new byte[1024 * 1024];
            int read;
            while ((read = in.read(buffer)) != -1) out.write(buffer, 0, read);
        }
    }
'''
if old not in text: raise SystemExit('Expected showAppList block was not found')
main.write_text(text.replace(old, new, 1))

emu = root / 'emu' / 'Emulator.java'
et = emu.read_text()
marker = '    private static native String[] getApps();\n'
if 'getInstalledAppsRaw' not in et:
    if marker not in et: raise SystemExit('Expected getApps native declaration was not found')
    wrapper = '''    public static String[] getInstalledAppsRaw() {
        checkInit();
        return getApps();
    }

'''
    emu.write_text(et.replace(marker, wrapper + marker, 1))

gradle = Path('eka2l1/src/emu/android/app/build.gradle')
g = gradle.read_text()
g = g.replace('applicationId "com.github.eka2l1"', 'applicationId "com.devilhandle.snakeex"')
g = g.replace('minifyEnabled true', 'minifyEnabled false')
gradle.write_text(g)

strings = Path('eka2l1/src/emu/android/app/src/main/res/values/strings.xml')
if strings.exists():
    s = strings.read_text()
    s = s.replace('<string name="app_name" translatable="false">EKA2L1</string>', '<string name="app_name" translatable="false">Snake EX</string>')
    strings.write_text(s)
