% Most Software Machine Data File

%% ScanImage

% Global microscope properties
objectiveResolution = 15;     % Resolution of the objective in microns/degree of scan angle

% Scanner systems
scannerNames = {'ResScanner'};     % Cell array of string names for each scan path in the microscope
scannerTypes = {'Linear'};     % Cell array indicating the type of scanner for each name. Current options: {'Resonant' 'Linear' 'SLM'}

% Simulated mode
simulated = true;     % Boolean for activating simulated mode. For normal operation, set to 'false'. For operation without NI hardware attached, set to 'true'.

% Optional components
components = {};     % Cell array of optional components to load. Ex: {'dabs.thorlabs.ECU1' 'dabs.thorlabs.BScope2'}

% Data file location
dataDir = '[MDF]\ConfigData';     % Directory to store persistent configuration and calibration data. '[MDF]' will be replaced by the MDF directory

% Custom Scripts
startUpScript = '';     % Name of script that is executed in workspace 'base' after scanimage initializes
shutDownScript = '';     % Name of script that is executed in workspace 'base' after scanimage exits

%% Shutters
% Shutter(s) used to prevent any beam exposure from reaching specimen during idle periods. Multiple
% shutters can be specified and will be assigned IDs in the order configured below.
shutterNames = {'Main Shutter'};     % Cell array specifying the display name for each shutter eg {'Shutter 1' 'Shutter 2'}
shutterDaqDevices = {'PXI1Slot3'};     % Cell array specifying the DAQ device or RIO devices for each shutter eg {'PXI1Slot3' 'PXI1Slot4'}
shutterChannelIDs = {'PFI12'};     % Cell array specifying the corresponding channel on the device for each shutter eg {'PFI12'}

shutterOpenLevel = true;     % Logical or 0/1 scalar indicating TTL level (0=LO;1=HI) corresponding to shutter open state for each shutter line. If scalar, value applies to all shutterLineIDs
shutterOpenTime = 0.1;     % Time, in seconds, to delay following certain shutter open commands (e.g. between stack slices), allowing shutter to fully open before proceeding.

%% Beams
beamDaqDevices = {};     % Cell array of strings listing beam DAQs in the system. Each scanner set can be assigned one beam DAQ ex: {'PXI1Slot4'}

% Define the parameters below for each beam DAQ specified above, in the format beamDaqs(N).param = ...
beamDaqs(1).modifiedLineClockIn = '';     % one of {PFI0..15, ''} to which external beam trigger is connected. Leave empty for automatic routing via PXI/RTSI bus
beamDaqs(1).frameClockIn = '';     % one of {PFI0..15, ''} to which external frame clock is connected. Leave empty for automatic routing via PXI/RTSI bus
beamDaqs(1).referenceClockIn = '';     % one of {PFI0..15, ''} to which external reference clock is connected. Leave empty for automatic routing via PXI/RTSI bus
beamDaqs(1).referenceClockRate = 1e+07;     % if referenceClockIn is used, referenceClockRate defines the rate of the reference clock in Hz. Default: 10e6Hz

beamDaqs(1).chanIDs = [];     % Array of integers specifying AO channel IDs, one for each beam modulation channel. Length of array determines number of 'beams'.
beamDaqs(1).displayNames = {};     % Optional string cell array of identifiers for each beam
beamDaqs(1).voltageRanges = 1.5;     % Scalar or array of values specifying voltage range to use for each beam. Scalar applies to each beam.

beamDaqs(1).calInputChanIDs = [];     % Array of integers specifying AI channel IDs, one for each beam modulation channel. Values of nan specify no calibration for particular beam.
beamDaqs(1).calOffsets = [];     % Array of beam calibration offset voltages for each beam calibration channel
beamDaqs(1).calUseRejectedLight = false;     % Scalar or array indicating if rejected light (rather than transmitted light) for each beam's modulation device should be used to calibrate the transmission curve
beamDaqs(1).calOpenShutterIDs = [];     % Array of shutter IDs that must be opened for calibration (ie shutters before light modulation device).

%% Motors
% Motor used for X/Y/Z motion, including stacks.

motors(1).controllerType = '';     % If supplied, one of {'sutter.mp285', 'sutter.mpc200', 'thorlabs.mcm3000', 'thorlabs.mcm5000', 'scientifica', 'pi.e665', 'pi.e816', 'npoint.lc40x', 'bruker.MAMC'}.
motors(1).dimensions = '';     % Assignment of stage dimensions to SI dimensions. Can be any combination of X,Y,Z, and R.
motors(1).comPort = [];     % Integer identifying COM port for controller, if using serial communication
motors(1).customArgs = {};     % Additional arguments to stage controller. Some controller require a valid stageType be specified
motors(1).invertDim = '';     % string with one character for each dimension specifying if the dimension should be inverted. '+' for normal, '-' for inverted
motors(1).positionDeviceUnits = [];     % 1xN array specifying, in meters, raw units in which motor controller reports position. If unspecified, default positionDeviceUnits for stage/controller type presumed.
motors(1).velocitySlow = [];     % Velocity to use for moves smaller than motorFastMotionThreshold value. If unspecified, default value used for controller. Specified in units appropriate to controller type.
motors(1).velocityFast = [];     % Velocity to use for moves larger than motorFastMotionThreshold value. If unspecified, default value used for controller. Specified in units appropriate to controller type.
motors(1).moveCompleteDelay = [];     % Delay from when stage controller reports move is complete until move is actually considered complete. Allows settling time for motor
motors(1).moveTimeout = [];     % Default: 2s. Fixed time to wait for motor to complete movement before throwing a timeout error
motors(1).moveTimeoutFactor = [];     % (s/um) Time to add to timeout duration based on distance of motor move command

%% FastZ
% FastZ hardware used for fast axial motion, supporting fast stacks and/or volume imaging

actuators(1).controllerType = '';     % If supplied, one of {'pi.e665', 'pi.e816', 'npoint.lc40x', 'analog'}.
actuators(1).comPort = [];     % Integer identifying COM port for controller, if using serial communication
actuators(1).customArgs = {};     % Additional arguments to stage controller
actuators(1).daqDeviceName = '';     % String specifying device name used for FastZ control; Specify SLM Scanner name if FastZ device is a SLM
actuators(1).frameClockIn = '';     % One of {PFI0..15, ''} to which external frame trigger is connected. Leave empty for automatic routing via PXI/RTSI bus
actuators(1).cmdOutputChanID = [];     % AO channel number (e.g. 0) used for analog position control
actuators(1).sensorInputChanID = [];     % AI channel number (e.g. 0) used for analog position sensing
actuators(1).commandVoltsPerMicron = 0.1;     % Conversion factor for desired command position in um to output voltage
actuators(1).commandVoltsOffset = 0;     % Offset in volts for desired command position in um to output voltage
actuators(1).sensorVoltsPerMicron = [];     % Conversion factor from sensor signal voltage to actuator position in um. Leave empty for automatic calibration
actuators(1).sensorVoltsOffset = [];     % Sensor signal voltage offset. Leave empty for automatic calibration
actuators(1).maxCommandVolts = [];     % Maximum allowable voltage command
actuators(1).maxCommandPosn = [];     % Maximum allowable position command in microns
actuators(1).minCommandVolts = [];     % Minimum allowable voltage command
actuators(1).minCommandPosn = [];     % Minimum allowable position command in microns
actuators(1).optimizationFcn = '';     % Function for waveform optimization
actuators(1).affectedScanners = {};     % If this actuator only changes the focus for an individual scanner, enter the name

% Field curvature correction params
fieldCurveZ0 = 0;
fieldCurveRx0 = 0;
fieldCurveRy0 = 0;
fieldCurveZ1 = 0;
fieldCurveRx1 = 0;
fieldCurveRy1 = 0;

%% ResScan (ResScanner)
nominalResScanFreq = 7910;     % [Hz] nominal frequency of the resonant scanner
beamDaqID = [];     % Numeric: ID of the beam DAQ to use with the resonant scan system
shutterIDs = 1;     % Array of the shutter IDs that must be opened for resonant scan system to operate

digitalIODeviceName = 'PXI1Slot3';     % String: Device name of the DAQ board or FlexRIO FPGA that is used for digital inputs/outputs (triggers/clocks etc). If it is a DAQ device, it must be installed in the same PXI chassis as the FlexRIO Digitizer

fpgaModuleType = 'NI7961';     % String: Type of FlexRIO FPGA module in use. One of {'NI7961' 'NI7975'}
digitizerModuleType = 'NI5734';     % String: Type of digitizer adapter module in use. One of {'NI5732' 'NI5734'}
rioDeviceID = 'RIO0';     % FlexRIO Device ID as specified in MAX. If empty, defaults to 'RIO0'
channelsInvert = [false false false false];     % Logical: Specifies if the input signal is inverted (i.e., more negative for increased light signal)

externalSampleClock = false;     % Logical: use external sample clock connected to the CLK IN terminal of the FlexRIO digitizer module
externalSampleClockRate = [];     % [Hz]: nominal frequency of the external sample clock connected to the CLK IN terminal (e.g. 80e6); actual rate is measured on FPGA

enableRefClkOutput = false;     % Enables/disables the 10MHz reference clock output on PFI14 of the digitalIODevice

% Galvo mirror settings
galvoDeviceName = 'PXI1Slot3';     % String identifying the NI-DAQ board to be used to control the galvo(s). The name of the DAQ-Device can be seen in NI MAX. e.g. 'Dev1' or 'PXI1Slot3'. This DAQ board needs to be installed in the same PXI chassis as the FPGA board specified in section
galvoAOChanIDX = [];     % The numeric ID of the Analog Output channel to be used to control the X Galvo. Can be empty for standard Resonant Galvo scanners.
galvoAOChanIDY = 1;     % The numeric ID of the Analog Output channel to be used to control the Y Galvo.

galvoAIChanIDX = [];     % The numeric ID of the Analog Input channel for the X Galvo feedback signal.
galvoAIChanIDY = [];     % The numeric ID of the Analog Input channel for the Y Galvo feedback signal.

xGalvoAngularRange = 15;     % max range in optical degrees (pk-pk) for x galvo if present
yGalvoAngularRange = 15;     % max range in optical degrees (pk-pk) for y galvo

galvoVoltsPerOpticalDegreeX = 1;     % galvo conversion factor from optical degrees to volts (negative values invert scan direction)
galvoVoltsPerOpticalDegreeY = 1;     % galvo conversion factor from optical degrees to volts (negative values invert scan direction)

galvoParkDegreesX = -8;     % Numeric [deg]: Optical degrees from center position for X galvo to park at when scanning is inactive
galvoParkDegreesY = -8;     % Numeric [deg]: Optical degrees from center position for Y galvo to park at when scanning is inactive

% Resonant mirror settings
resonantZoomDeviceName = 'PXI1Slot3';     % String identifying the NI-DAQ board to host the resonant zoom analog output. Leave empty to use same board as specified in 'galvoDeviceName'
resonantZoomAOChanID = 0;     % resonantZoomAOChanID: The numeric ID of the Analog Output channel to be used to control the Resonant Scanner Zoom level.
resonantEnableTerminal = [];     % (optional) The PFI line on the resonantZoomDevice that enables/disables the resonant scanner. Example: 13   Not required for Thorlabs BSCope

resonantAngularRange = 15;     % max range in optical degrees (pk-pk) for resonant
rScanVoltsPerOpticalDegree = 0.3333;     % resonant scanner conversion factor from optical degrees to volts

resonantScannerSettleTime = 0.5;     % [seconds] time to wait for the resonant scanner to reach its desired frequency after an update of the zoomFactor

% Advanced/Optional
PeriodClockDebounceTime = 1e-07;     % [s] time the period clock has to be stable before a change is registered
TriggerDebounceTime = 5e-07;     % [s] time acquisition, stop and next trigger to be stable before a change is registered
reverseLineRead = false;     % flips the image in the resonant scan axis
bitfileAppendix = '';     % apendix to bitfile name. Allows to choose from different bitfiles for the same FPGA/digitizer combination

% Aux Trigger Recording, Photon Counting, and I2C are mutually exclusive

% Aux Trigger Recording
auxTriggersEnable = true;
auxTriggersTimeDebounce = 1e-06;     % [s] time an aux trigger needs to be high for registering an edge (seconds)
auxTriggerLinesInvert = [false;false;false;false];     % [logical] 1x4 vector specifying polarity of aux trigger inputs

% Photon Counting
photonCountingEnable = false;
photonCountingDisableAveraging = [];     % disable averaging of samples into pixels; instead accumulate samples
photonCountingScaleByPowerOfTwo = 8;     % for use with photonCountingDisableAveraging == false; scale count by 2^n before averaging to avoid loss of precision by integer division
photonCountingDebounce = 2.5e-08;     % [s] time the TTL input needs to be stable high before a pulse is registered

% I2C
I2CEnable = false;
I2CAddress = 0;     % [byte] I2C address of the FPGA
I2CDebounce = 5e-07;     % [s] time the I2C signal has to be stable high before a change is registered
I2CStoreAsChar = false;     % if false, the I2C packet bytes are stored as a uint8 array. if true, the I2C packet bytes are stored as a string. Note: a Null byte in the packet terminates the string
I2CDisableAckOutput = false;     % the FPGA confirms each packet with an ACK bit by actively pulling down the SDA line. I2C_DISABLE_ACK_OUTPUT = true disables the FPGA output

% Laser Trigger
LaserTriggerPort = '';     % Port on FlexRIO AM digital breakout (DIO0.[0:3]) where laser trigger is connected.
LaserTriggerFilterTicks = 0;
LaserTriggerSampleMaskEnable = false;
LaserTriggerSampleWindow = [0 1];

%% LinScan (ResScanner)
deviceNameAcq = 'PXI1Slot3';     % string identifying NI DAQ board for PMT channels input
deviceNameGalvo = 'PXI1Slot3';     % string identifying NI DAQ board for controlling X/Y galvo. leave empty if same as deviceNameAcq
deviceNameAux = 'PXI1Slot3';     % string identifying NI DAQ board for outputting clocks. leave empty if unused. Must be a X-series board

% Optional
channelsInvert = [false false false false];     % scalar or vector identifiying channels to invert. if scalar, the value is applied to all channels
beamDaqID = [];     % Numeric: ID of the beam DAQ to use with the linear scan system
shutterIDs = 1;     % Array of the shutter IDs that must be opened for linear scan system to operate

referenceClockIn = '';     % one of {'',PFI14} to which 10MHz reference clock is connected on Aux board. Leave empty for automatic routing via PXI bus
enableRefClkOutput = 0;     % Enables/disables the export of the 10MHz reference clock on PFI14

% Acquisition
channelIDs = [0 1 2 3];     % Array of numeric channel IDs for PMT inputs. Leave empty for default channels (AI0...AIN-1)

% Scanner control
XMirrorChannelID = 0;     % The numeric ID of the Analog Output channel to be used to control the X Galvo.
YMirrorChannelID = 1;     % The numeric ID of the Analog Output channel to be used to control the y Galvo.

xGalvoAngularRange = 15;     % max range in optical degrees (pk-pk) for x galvo
yGalvoAngularRange = 15;     % max range in optical degrees (pk-pk) for y galvo

voltsPerOpticalDegreeX = 1;     % galvo conversion factor from optical degrees to volts (negative values invert scan direction)
voltsPerOpticalDegreeY = 1;     % galvo conversion factor from optical degrees to volts (negative values invert scan direction)

scanParkAngleX = -7.5;     % Numeric [deg]: Optical degrees from center position for X galvo to park at when scanning is inactive
scanParkAngleY = -7.5;     % Numeric [deg]: Optical degrees from center position for Y galvo to park at when scanning is inactive

% Optional: Scanner position feedback
deviceNameGalvoFeedback = '';     % string identifying NI DAQ board that reads the galvo position feedback signals. Leave empty if they are on deviceNameGalvo. Cannot be the same as deviceNameAcq when using for line scanning
XMirrorPosChannelID = [];     % The numeric ID of the Analog Input channel to be used to read the X Galvo position (optional).
XMirrorPosTermCfg = 'Differential';     % AI terminal configuration to be used for reading X-galvo position
YMirrorPosChannelID = [];     % The numeric ID of the Analog Input channel to be used to read the y Galvo position (optional).
YMirrorPosTermCfg = 'Differential';     % AI terminal configuration to be used for reading Y-galvo position

% Optional: Mirror position offset outputs for motion correction
deviceNameOffset = '';     % string identifying NI DAQ board that hosts the offset analog outputs
XMirrorOffsetChannelID = 0;     % numeric ID of the Analog Output channel to be used to control the X Galvo offset.
YMirrorOffsetChannelID = 1;     % numeric ID of the Analog Output channel to be used to control the y Galvo offset.

XMirrorOffsetMaxVoltage = 1;     % maximum allowed voltage output for the channel specified in XMirrorOffsetChannelID
YMirrorOffsetMaxVoltage = 1;     % maximum allowed voltage output for the channel specified in YMirrorOffsetChannelID

% Advanced/Optional:
stripingEnable = true;     % enables/disables striping display
stripingMaxRate = 10;     % [Hz] determines the maximum display update rate for striping
maxDisplayRate = 30;     % [Hz] limits the maximum display rate (affects frame batching)
internalRefClockSrc = '';     % Reference clock to use internally
internalRefClockRate = [];     % Rate of reference clock to use internally
secondaryFpgaFifo = false;     % specifies if the secondary fpga fifo should be used

% Laser Trigger
LaserTriggerPort = '';     % Port on FlexRIO AM digital breakout (DIO0.[0:3]) or digital IO DAQ (PFI[0:23]) where laser trigger is connected.
LaserTriggerFilterTicks = 0;
LaserTriggerSampleMaskEnable = false;
LaserTriggerSampleWindow = [0 1];

