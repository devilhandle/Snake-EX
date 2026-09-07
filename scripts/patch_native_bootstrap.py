from pathlib import Path

main_activity = Path('eka2l1/src/emu/android/app/src/main/java/com/github/eka2l1/MainActivity.java')
thread_cpp = Path('eka2l1/src/emu/android/app/src/main/cpp/src/thread.cpp')

if not main_activity.exists():
    raise SystemExit(f'Missing MainActivity: {main_activity}')

text = main_activity.read_text()
old = '''            Emulator.initializeForShortcutLaunch(this);\n            bootstrapAndLaunch();'''
new = '''            // The native EKA2L1 bootstrap needs a device to exist before stage_two().\n            // Put the bundled Nokia 6600 ROM in the emulator storage before startNative().\n            Emulator.initializePath(this);\n            Emulator.initializeFolders();\n            copyBundledRomForNativeBootstrap();\n            Emulator.initializeForShortcutLaunch(this);\n            bootstrapAndLaunch();'''
if old in text:
    text = text.replace(old, new, 1)

method = '''    private void copyBundledRomForNativeBootstrap() {\n        File out = new File(Emulator.getEmulatorDir(), "storage/bundled_nokia6600.dmp");\n        copyAssetIfNeeded(ROM_ASSET, out);\n    }\n\n'''
if 'private void copyBundledRomForNativeBootstrap()' not in text:
    marker = '    private void bootstrapAndLaunch() {'
    if marker not in text:
        raise SystemExit('bootstrapAndLaunch marker not found')
    text = text.replace(marker, method + marker, 1)
main_activity.write_text(text)

if not thread_cpp.exists():
    raise SystemExit(f'Missing Android native thread source: {thread_cpp}')

cpp = thread_cpp.read_text()
old_cpp = '''        state.stage_one();\n\n        const bool result = state.stage_two();'''
new_cpp = '''        state.stage_one();\n\n        // A bundled Snake EX build has no pre-installed EKA2L1 device on first run.\n        // stage_two() refuses to continue without a current device, so install the\n        // bundled Nokia 6600 ROM after stage_one() has created the native system,\n        // but before stage_two() starts the Symbian runtime.\n        if (state.symsys->get_device_manager()->total() == 0 && state.launcher) {\n            std::string bundled_rom = eka2l1::add_path(state.conf.storage,\n                "bundled_nokia6600.dmp");\n            std::string empty_rpkg;\n            state.launcher->install_device(empty_rpkg, bundled_rom, false);\n            state.symsys->rescan_devices(drive_z);\n            if (state.symsys->get_device_manager()->total() > 0) {\n                state.symsys->set_device(0);\n            }\n        }\n\n        const bool result = state.stage_two();'''
if old_cpp not in cpp:
    raise SystemExit('Android emulator_entry stage_one/stage_two block not found')
cpp = cpp.replace(old_cpp, new_cpp, 1)
thread_cpp.write_text(cpp)

print('Patched bundled Nokia 6600 ROM installation before EKA2L1 stage_two().')
