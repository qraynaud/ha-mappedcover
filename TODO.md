# TODO

- [x] **Project Setup**
  - [x] Ensure `custom_components/mappedcover/` exists with `__init__.py`, `manifest.json`, `sensor.py`, `const.py`
  - [x] Update `manifest.json` with correct domain, name, and metadata

- [x] **Config Flow**
  - [x] Implement `config_flow.py` to allow UI-based configuration
  - [x] Prompt user to select an existing cover entity (exclude covers from this integration)
  - [x] Create the new cover with an ID and default name derived from the mapped cover
  - [x] Allow reconfiguration of each new entity using the UI

- [x] **Remapping Logic**
  - [x] Add options for:
    - [x] Max position (user-defined)
    - [x] Min position (user-defined, 0 still maps to 0)
    - [x] Detect if the selected cover supports tilt
    - [x] Max tilt position (if supported, user-defined)
    - [x] Min tilt position (if supported, user-defined, 0 still maps to 0)
  - [x] Store remapping configuration

- [x] **Entity Creation**
  - [x] Create a new cover entity representing the remapped cover
  - [x] Forward commands to the selected cover, remapping positions/tilts as configured

- [x] **State Reporting**
  - [x] Always report the target position/tilt as the current state while moving
  - [x] Sync state with the underlying cover when not moving

- [ ] **Unit Testing**
  - [ ] **Config Flow**
    - [ ] Test that the config flow UI displays all required fields (entity selection, ID, name, min/max position, min/max tilt if supported)
    - [ ] Test that only valid, non-mapped cover entities are selectable
    - [ ] Test that submitting the config flow creates an entry with the correct data
    - [ ] Test that min/max values are validated and stored as expected
    - [ ] Test that tilt options are only shown if the selected entity supports tilt
  - [ ] **Reconfiguration (Options Flow)**
    - [ ] Test that the options flow can be started for an existing mapped cover
    - [ ] Test that changing min/max position/tilt updates the entity's behavior
    - [ ] Test that changes persist after Home Assistant restart
    - [ ] Test that the UI reflects current configuration values
  - [ ] **Cover Entity Logic**
    - [ ] **Entity Creation & Initialization**
      - [ ] Test that a mapped cover entity is created with the correct name, unique_id, and device_info
      - [ ] Test that the entity is available/unavailable based on the underlying cover
    - [ ] **Remapping Logic**
      - [ ] Test that user 0 always maps to source 0 for position and tilt
      - [ ] Test that user 1–100 maps linearly to min..max for position and tilt
      - [ ] Test that remapping is correct for edge values (min, max, midpoints)
      - [ ] Test that remapping is correct for custom min/max values
    - [ ] **Command Forwarding**
      - [ ] Test that set_cover_position calls the underlying entity with remapped value
      - [ ] Test that set_cover_tilt_position calls the underlying entity with remapped value
      - [ ] Test that open/close/stop/tilt commands are forwarded and remapped
      - [ ] Test that rapid command changes are handled without blocking
    - [ ] **State Reporting**
      - [ ] Test that while moving, the entity reports the target position/tilt
      - [ ] Test that after movement, the entity syncs with the underlying state
      - [ ] Test that the entity reports unavailable if the underlying entity is unavailable
      - [ ] Test that the state property returns 'open', 'closed', 'opening', 'closing' as appropriate
    - [ ] **Underlying cover Quirks**
      - [ ] Test that if the underlying cover forgets tilt/position, the integration retries as needed
      - [ ] Test that sequential moves (position then tilt, or vice versa) are handled correctly
    - [ ] **Concurrency & Responsiveness**
      - [ ] Test that only one converge_position runs at a time and new targets interrupt the previous run
      - [ ] Test that the entity remains responsive to rapid user commands
      - [ ] Test that stop commands immediately interrupt any ongoing move
    - [ ] **Device Class Reflection**
      - [ ] Test that the mapped cover's device_class matches the underlying cover's device_class
      - [ ] Test that changes to the underlying device_class are reflected in the mapped entity
    - [ ] **Error & Edge Case Handling**
      - [ ] Test that the entity handles unavailable/unknown states gracefully
      - [ ] Test that unsupported features (e.g., no tilt) are not exposed in supported_features
      - [ ] Test that invalid remapping configuration is handled with a clear error or fallback

- [ ] **Documentation**
  - [ ] Update `README.md` with configuration and usage instructions
  - [ ] Add examples for remapping scenarios

- [ ] **HACS Compatibility**
  - [ ] Add `info.md` and ensure repository structure matches HACS requirements

- [ ] **Polish**
  - [ ] Code cleanup and comments
  - [ ] Add MIT License file