import obspython as obs
import pyautogui
import json
from screeninfo import get_monitors

# global variables/definitions
monitors = []
# use to hold all the details needed to make a swap
switcher_array = []
# used to only call swapping a scene when needed
current_scene = ""
# max monitor width
max_monitor_width = 1000000
# max monitor height
max_monitor_height = 1000000
# complete add
complete_add_state = False
# current virtual monitor
virtual_monitors = []
settings_ref = None

add_virtual_names = ["monitor_name", "x_start", "v_width", "v_height", "add_virtual_display"]

class Monitor:
    def __init__(self, name, x, y, width, height) -> None:
        self.name = name
        self.x = x
        self.y = y
        self.height = height
        self.width = width
        

def set_virtual_monitors():
    global virtual_monitors, settings_ref
    v_dict = {}
    for mon in virtual_monitors:
        v_dict[mon.name] = {
            "name": mon.name,
            "x": mon.x,
            "y": mon.y,
            "width": mon.width,
            "height": mon.height
        }
    obs.obs_data_set_string(settings_ref, "virtual_monitors", json.dumps(v_dict))

def get_virtual_monitors():
    global virtual_monitors, settings_ref
    vm = obs.obs_data_get_string(settings_ref, "virtual_monitors")
    try:
        vm = json.loads(vm)
    except:
        return []
    monitors = []
    for _,value in vm.items():
        monitors.append(Monitor(
            value["name"],
            value["x"],
            value["y"],
            value["width"],
            value["height"]
        ))
    virtual_monitors = monitors
    return virtual_monitors

def add_virtual(props, data):
    global adding_virtual, max_monitor_width
    # have to do this way
    obs.obs_properties_remove_by_name(props, "add_virtual_display")
    obs.obs_properties_add_text(props, "monitor_name", "Name", obs.OBS_TEXT_DEFAULT)
    obs.obs_properties_add_int(props, "x_start", "Start X", 0, max_monitor_width, 1)
    obs.obs_properties_add_int(props, "v_width", "Width", 0, max_monitor_width, 1)
    obs.obs_properties_add_int(props, "v_height", "Height", 0, max_monitor_height, 1)
    
    obs.obs_properties_add_button(props, "add_virtual_display", "Complete Add", complete_add)
    return True

def complete_add(props, data):
    global monitors, add_virtual_names, complete_add_state, settings_ref, virtual_monitors
    new_virtual = get_virtual_monitor(settings_ref)
    virtual_monitors.append(new_virtual)
    monitors = get_monitors()
    monitors.extend(virtual_monitors)
    complete_add_state = True
    for name in add_virtual_names:
        obs.obs_properties_remove_by_name(props, name)
    obs.obs_properties_add_button(props, "add_virtual_display", "Add Virtual", add_virtual)
    set_virtual_monitors()
    
    return True

class Switcher:
    def __init__(self, scene, monitor):
        self.scene = scene
        self.monitor = monitor

# description displayed in the Scripts dialog window
def script_description():
    return "Auto move scenes to where the mouse position is based on what monitor your cursor is in\n\nNOTE: If you change your monitor layout, you will need to either reload this plugin or change a setting"

# setup defaults
def script_defaults(settings):
    global settings_ref
    settings_ref = settings
    get_virtual_monitors()
    # make all switching enabled by default
    for i in range(len(monitors)):
        obs.obs_data_set_default_bool(settings, "switcher_enabled_{}".format(i), True)



# Called to display the properties GUI
def script_properties():
    global monitors, adding_virtual
    # setup the properties
    props = obs.obs_properties_create()
    # for each monitor, set a scene that you want to move to
    for i in range(len(monitors)):
        offset_num = i + 1
        # enable vs disabled
        obs.obs_properties_add_bool(props, "switcher_enabled_{}".format(i), "Enable Switching".format(offset_num))
        # available scenes to swap to
        scene_list = obs.obs_properties_add_list(props, "scene_{}".format(i), "Scene {} Name".format(offset_num), obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
        # list of monitors to use for detecting which monitor the mouse is on
        monitor_list = obs.obs_properties_add_list(props, "monitor_{}_select".format(i), "Monitor {} Select".format(offset_num), obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_STRING)
        # iterate through scenes to add the options to the UI
        for scene in obs.obs_frontend_get_scenes():
            name = obs.obs_source_get_name(scene)
            obs.obs_property_list_add_string(scene_list, name, name)
            # must release - apparently you're supposed to treat the python API like the C++ API
            obs.obs_source_release(scene)
        # iterate through the monitors, adding them as options to the array
        for j in range(len(monitors)):
            obs.obs_property_list_add_string(monitor_list, "Monitor {} - {}".format(j+1, monitors[j].name), str(j))

    # add button to create virtual monitor
    obs.obs_properties_add_button(props, "add_virtual_display", "Add Virtual", add_virtual)
    
    return props


def get_virtual_monitor(settings):
    monitor = Monitor(
        obs.obs_data_get_string(settings, "monitor_name"),
        obs.obs_data_get_int(settings, "x_start"),
        0,
        obs.obs_data_get_int(settings, "v_width"),
        obs.obs_data_get_int(settings, "v_height")
    )
    return monitor
    

# Called after change of settings including once after script load
def script_update(settings):
    global monitors, switcher_array, settings_ref
    # get the monitors
    
    settings_ref = settings

    monitors = get_monitors()
    monitors.extend(virtual_monitors)
    # sort by the x value, from just testing at home, x value dictates left to right
    monitors.sort(key=lambda m: m.x)
    switcher_array = []
    # go through monitors
    for i in range(len(monitors)):
        # get if this switcher is enabled
        enabled = obs.obs_data_get_bool(settings, "switcher_enabled_{}".format(i))
        if not enabled:
            continue
        # pull the scene scene name and monitor str
        scene = obs.obs_data_get_string(settings, "scene_{}".format(i))
        monitor_str = obs.obs_data_get_string(settings, "monitor_{}_select".format(i))
        try:
            # the monitor value maps to its index in the monitor array, try to index in
            monitor = monitors[int(monitor_str)]
        except:
            # continue if monitor str isn't able to index in
            continue
       
        
        # append a new switcher with those details
        switcher_array.append(Switcher(scene, monitor))


# called every frame
def script_tick(seconds):
    global monitors, current_scene, switcher_array
    # get position
    point = pyautogui.position()
    # if we don't have switchers, do nothing
    if len(switcher_array) == 0:
        return
    for switcher in switcher_array:
        monitor = switcher.monitor
        # outside of the range
        not_in_x = (point.x < monitor.x or point.x >= monitor.x + monitor.width)
        not_in_y = (point.y < monitor.y or point.y >= monitor.y + monitor.height)
        # DEBUG
        # print("In X: {}, In Y: {}".format(not not_in_x, not not_in_y))
        if not_in_x or not_in_y:
            continue
        # inside the range
        name = switcher.scene
        if name == current_scene:
            continue
        # name was different from the current scene, swap to it
        set_scene_from_name(name)
        current_scene = name
        print("scene swapped to: {}".format(name))
        break

    

def set_scene_from_name(in_name):
    found = False
    for scene in obs.obs_frontend_get_scenes():
        # need to ensure we release all of the scenes
        if not found:
            name = obs.obs_source_get_name(scene)
            if name != in_name:
                continue
            # found the name
            found = True
            obs.obs_frontend_set_current_scene(scene)
        obs.obs_source_release(scene)
    

# Called before data settings are saved
def script_save(settings):
  pass