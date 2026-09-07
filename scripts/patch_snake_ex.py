from pathlib import Path

# Java sources live under the emu package; MainActivity is in the parent package.
java_root = Path('eka2l1/src/emu/android/app/src/main/java/com/github/eka2l1')
emu_root = java_root / 'emu'
main = java_root / 'MainActivity.java'
text = main.read_text()
text = text.replace('import android.os.Bundle;\n', 'import android.os.Bundle;\nimport java.io.File;\nimport java.io.IOException;\n')

# Dedicated launcher: never show the stock storage warning or the app list.
old_init = '''    private void initialize() {
        ActivityManager activityManager = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        ConfigurationInfo configurationInfo = activityManager.getDeviceConfigurationInfo();
        if (configurationInfo.reqGlEsVersion < 0x30000) {
            showOpenGLDialog();
            return;
        }

        AppDataStore dataStore = AppDataStore.getAndroidStore();
        boolean warningShown = dataStore.getBoolean(PREF_STORAGE_WARNING_SHOWN, false);
        if (!FileUtils.isExternalStorageLegacy() && !warningShown) {
            showScopedStorageDialog();
            dataStore.putBoolean(PREF_STORAGE_WARNING_SHOWN, true);
            dataStore.save();
            return;
        }

        showAppList();
    }
'''
new_init = '''    private void initialize() {
        ActivityManager activityManager = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        ConfigurationInfo configurationInfo = activityManager.getDeviceConfigurationInfo();
        if (configurationInfo.reqGlEsVersion < 0x30000) {
            showOpenGLDialog();
            return;
        }

        showAppList();
    }
'''
if old_init not in text: raise SystemExit('Expected initialize block was not found')
text = text.replace(old_init, new_init, 1)

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
        // Native EKA2L1 initialization must happen on the Activity thread.
        Emulator.initializeForShortcutLaunch(this);
        launchSnakeEx();
    }

    private void launchSnakeEx() {
        new Thread(() -> {
            try {
                File gameDir = new File(getFilesDir(), "snakeex");
                if (!gameDir.exists() && !gameDir.mkdirs()) throw new IOException("Cannot create game directory");
                File romFile = new File(gameDir, "nokia6600.rom");
                File sisFile = new File(gameDir, "Snake EX-2.sis");
                copyAssetIfNeeded("snakeex/nokia6600.rom", romFile);
                copyAssetIfNeeded("snakeex/Snake EX-2.sis", sisFile);

                if (Emulator.getDevices().length == 0) {
                    int result = Emulator.installDevice("", romFile.getAbsolutePath(), false);
                    if (result != Emulator.INSTALL_DEVICE_ERROR_NONE && result != Emulator.INSTALL_DEVICE_ERROR_ALREADY_EXIST) {
                        throw new IOException("Nokia 6600 ROM install failed: " + result);
                    }
                }

                String[] deviceCodes = Emulator.getDeviceFirmwareCodes();
                if (deviceCodes.length == 0) throw new IOException("Nokia 6600 device was not created");
                Emulator.setCurrentDevice(0, true);

                long snakeUid = -1;
                String snakeName = "Snake EX";
                String[] apps = Emulator.getInstalledAppsRaw();
                for (int i = 0; i + 1 < apps.length; i += 2) {
                    String name = apps[i + 1];
                    if (name != null && name.toLowerCase(java.util.Locale.ROOT).contains("snake")) {
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
                        if (name != null && name.toLowerCase(java.util.Locale.ROOT).contains("snake")) {
                            snakeUid = Long.parseLong(apps[i]);
                            snakeName = name;
                            break;
                        }
                    }
                }

                if (snakeUid < 0) throw new IOException("Snake EX application UID was not found after installation");

                final long uid = snakeUid;
                final String name = snakeName;
                final String deviceCode = deviceCodes[0];
                runOnUiThread(() -> {
                    // Match EKA2L1's normal app-list launch path. Do not mark this
                    // as a shortcut: EmulatorActivity then uses its normal game
                    // initialization path instead of reinitializing native state
                    // before super.onCreate().
                    Intent intent = new Intent(Intent.ACTION_DEFAULT, null, this,
                            com.github.eka2l1.emu.EmulatorActivity.class);
                    intent.putExtra(com.github.eka2l1.emu.Constants.KEY_APP_UID, uid);
                    intent.putExtra(com.github.eka2l1.emu.Constants.KEY_APP_NAME, name);
                    intent.putExtra(com.github.eka2l1.emu.Constants.KEY_DEVICE_CODE, deviceCode);
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

# Dedicated build: never open EKA2L1's configuration screen on first launch.
emu_activity = emu_root / 'EmulatorActivity.java'
et = emu_activity.read_text()
old_profile = '''        if (externalIntent && (params = ProfilesManager.loadConfig(configDir)) == null) {
            Intent configIntent = new Intent(this, ConfigActivity.class);
            Bundle extras;
            if (launchFromFile) {
                extras = new Bundle();

                extras.putLong(KEY_APP_UID, uid);
                extras.putString(KEY_APP_NAME, name);
                extras.putString(KEY_DEVICE_CODE, deviceCode);
            } else {
                extras = Objects.requireNonNull(intent.getExtras());
            }
            extras.putString(KEY_ACTION, ACTION_EDIT);
            configIntent.putExtras(extras);
            startActivity(configIntent);
            finish();
            return;
        } else {
            params = ProfilesManager.loadConfigOrDefault(configDir, defProfile);
        }
'''
new_profile = '''        // Dedicated Snake EX build: use EKA2L1's default profile immediately.
        // Never open the configuration UI for the user.
        params = ProfilesManager.loadConfigOrDefault(configDir, defProfile);
'''
if old_profile not in et: raise SystemExit('Expected EmulatorActivity profile block was not found')
emu_activity.write_text(et.replace(old_profile, new_profile, 1))

# Public wrapper around the native installed-app lookup.
emu = emu_root / 'Emulator.java'
et = emu.read_text()
marker = '    private static native String[] getApps();\n'
wrapper = '''    public static String[] getInstalledAppsRaw() {
        checkInit();
        return getApps();
    }

'''
if 'getInstalledAppsRaw()' not in et:
    if marker not in et: raise SystemExit('Expected Emulator.getApps native declaration was not found')
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
