---
citation: 49 CFR Part 563
commodities:
- ECUs
id: us-cfr-part-563
last_pulled: '2026-06-01T18:44:10+00:00'
open_tags:
- event data recorder
- EDR
- crash data recording
- delta-V
- occupant restraint system
- air bag control unit
- ABS activity
- ignition cycle counter
- crash event data
- data retrieval tool
- frontal air bag deployment
- vehicle dynamics recording
region: US
source_api: ecfr
source_url: https://www.ecfr.gov/current/title-49/part-563
status: in-force
summary: Event data recorders (EDRs) in eligible motor vehicles are regulated for
  how they collect, store, and make retrievable crash event data. Manufacturers of
  passenger cars, multipurpose passenger vehicles, trucks, and buses with a GVWR of
  8,500 lbs or less (if equipped with an EDR) manufactured on or after September 1,...
summary_generated_at: '2026-06-22T17:48:27+00:00'
summary_hash: 086770e9f1494fe6eec970a7a5a901977f4b22d2
systems:
- Crashworthiness
- Restraints
- On-board diagnostics
tagged_at: '2026-06-16T15:44:40+00:00'
tagging_status: llm-tagged
title: PART 563—EVENT DATA RECORDERS
un_equivalent_ai:
- UN R160
vehicle_categories:
- Passenger car
- Light truck
- Bus
---

## PART 563—EVENT DATA RECORDERS

### § 563.1 Scope.

This part specifies uniform, national requirements for vehicles equipped with event data recorders (EDRs) concerning the collection, storage, and retrievability of onboard motor vehicle crash event data. It also specifies requirements for vehicle manufacturers to make tools and/or methods commercially available so that crash investigators and researchers are able to retrieve data from EDRs.

### § 563.2 Purpose.

The purpose of this part is to help ensure that EDRs record, in a readily usable manner, data valuable for effective crash investigations and for analysis of safety equipment performance (e.g., advanced restraint systems). These data will help provide a better understanding of the circumstances in which crashes and injuries occur and will lead to safer vehicle designs.

### § 563.3 Application.

This part applies to the following vehicles manufactured on or after September 1, 2012, if they are equipped with an event data recorder: passenger cars, multipurpose passenger vehicles, trucks, and buses with a GVWR of 3,855 kg (8,500 pounds) or less and an unloaded vehicle weight of 2,495 kg (5,500 pounds) or less, except for walk-in van-type trucks or vehicles designed to be sold exclusively to the U.S. Postal Service. This part also applies to manufacturers of those vehicles. However, vehicles manufactured before September 1, 2013 that are manufactured in two or more stages or that are altered (within the meaning of 49 CFR 567.7) after having been previously certified to the Federal motor vehicle safety standards in accordance with part 567 of this chapter need not meet the requirements of this part.

*[73 FR 2179, Jan. 14, 2008]*

### § 563.4 xxx

### § 563.5 Definitions.

(a) Motor vehicle safety standard definitions. Unless otherwise indicated, all terms that are used in this part and are defined in the Motor Vehicle Safety Standards, part 571 of this subchapter, are used as defined therein.

(b) Other definitions.

ABS activity means the anti-lock brake system (ABS) is actively controlling the vehicle's brakes.

Air bag warning lamp status means whether the warning lamp required by FMVSS No. 208 is on or off.

Capture means the process of buffering EDR data in a temporary, volatile storage medium where it is continuously updated at regular time intervals.

Delta-V, lateral means the cumulative change in velocity, as recorded by the EDR of the vehicle, along the lateral axis, starting from crash time zero and ending at 0.25 seconds, recorded every 0.01 seconds.

Delta-V, longitudinal means the cumulative change in velocity, as recorded by the EDR of the vehicle, along the longitudinal axis, starting from crash time zero and ending at 0.25 seconds, recorded every 0.01 seconds.

Deployment time, frontal air bag means (for both driver and right front passenger) the elapsed time from crash time zero to the deployment command, or for multi-staged air bag systems, the deployment command for the first stage.

Disposal means the deployment command of the second (or higher, if present) stage of a frontal air bag for the purpose of disposing the propellant from the air bag device.

End of event time means the moment at which the resultant cumulative delta-V within a 20 ms time period becomes 0.8 km/h (0.5 mph) or less, or the moment at which the crash detection algorithm of the air bag control unit resets.

Engine RPM means

(1) For vehicles powered by internal combustion engines, the number of revolutions per minute of the main crankshaft of the vehicle's engine; and

(2) For vehicles not entirely powered by internal combustion engines, the number of revolutions per minute of the motor shaft at the point at which it enters the vehicle transmission gearbox.

Engine throttle, percent full means the driver-requested acceleration as measured by the throttle position sensor on the accelerator pedal compared to the fully-depressed position.

Event means a crash or other physical occurrence that causes the trigger threshold to be met or exceeded, or any non-reversible deployable restraint to be deployed, whichever occurs first.

Event data recorder (EDR) means a device or function in a vehicle that records the vehicle's dynamic time-series data during the time period just prior to a crash event (e.g., vehicle speed vs. time) or during a crash event (e.g., delta-V vs. time), intended for retrieval after the crash event. For the purposes of this definition, the event data do not include audio and video data.

Frontal air bag means an inflatable restraint system that requires no action by vehicle occupants and is used to meet the applicable frontal crash protection requirements of FMVSS No. 208.

Ignition cycle, crash means the number (count) of power cycles applied to the recording device at the time when the crash event occurred since the first use of the EDR.

Ignition cycle download means the number (count) of power cycles applied to the recording device at the time when the data was downloaded since the first use of the EDR.

Lateral acceleration means the component of the vector acceleration of a point in the vehicle in the y-direction. The lateral acceleration is positive from left to right, from the perspective of the driver when seated in the vehicle facing the direction of forward vehicle travel.

Limited-line manufacturer means a manufacturer that sells three or fewer carlines, as that term is defined in 49 CFR 583.4, in the United States during a production year.

Longitudinal acceleration means the component of the vector acceleration of a point in the vehicle in the x-direction. The longitudinal acceleration is positive in the direction of forward vehicle travel.

Maximum delta-V, lateral means the maximum value of the cumulative change in velocity, as recorded by the EDR, of the vehicle along the lateral axis, starting from crash time zero and ending at 0.3 seconds.

Maximum delta-V, longitudinal means the maximum value of the cumulative change in velocity, as recorded by the EDR, of the vehicle along the longitudinal axis, starting from crash time zero and ending at 0.3 seconds.

Maximum delta-V, resultant means the time-correlated maximum value of the cumulative change in velocity, as recorded by the EDR or processed during data download, along the vector-added longitudinal and lateral axes.

Multi-event crash means the occurrence of 2 events, the first and last of which begin not more than 5 seconds apart.

Non-volatile memory means the memory reserved for maintaining recorded EDR data in a semi-permanent fashion. Data recorded in non-volatile memory is retained after loss of power and can be retrieved with EDR data extraction tools and methods.

Normal acceleration means the component of the vector acceleration of a point in the vehicle in the z-direction. The normal acceleration is positive in a downward direction and is zero when the accelerometer is at rest.

Occupant position classification means the classification indicating that the seating posture of a front outboard occupant (both driver and right front passenger) is determined as being out-of-position.

Occupant size classification means, for the right front passenger, the classification of the occupant as a child (as defined in 49 CFR part 572, subpart N or smaller) or not as an adult (as defined in 49 CFR part 572, subpart O), and for the driver, the classification of the driver as being a 5th percentile female (as defined in 49 CFR Part 572, subpart O) or larger.

Pretensioner means a device that is activated by a vehicle's crash sensing system and removes slack from a vehicle safety belt system.

Record means the process of saving captured EDR data into a non-volatile device for subsequent retrieval.

Safety belt status means the feedback from the safety system that is used to determine that an occupant's safety belt (for both driver and right front passenger) is fastened or unfastened.

Seat track position switch, foremost, status means the status of the switch that is installed to detect whether the seat is moved to a forward position.

Service brake, on or off means the status of the device that is installed in or connected to the brake pedal system to detect whether the pedal was pressed. The device can include the brake pedal switch or other driver-operated service brake control.

Side air bag means any inflatable occupant restraint device that is mounted to the seat or side structure of the vehicle interior, and that is designed to deploy in a side impact crash to help mitigate occupant injury and/or ejection.

Side curtain/tube air bag means any inflatable occupant restraint device that is mounted to the side structure of the vehicle interior, and that is designed to deploy in a side impact crash or rollover and to help mitigate occupant injury and/or ejection.

Small-volume manufacturer means an original vehicle manufacturer that produces or assembles fewer than 5,000 vehicles annually for sale in the United States.

Speed, vehicle indicated means the vehicle speed indicated by a manufacturer-designated subsystem designed to indicate the vehicle's ground travel speed during vehicle operation.

Stability control means any device that complies with FMVSS No. 126, “Electronic stability control systems.”

Steering input means the angular displacement of the steering wheel measured from the straight-ahead position (position corresponding to zero average steer angle of a pair of steered wheels).

Suppression switch status means the status of the switch indicating whether an air bag suppression system is on or off.

Time from event 1 to 2 means the elapsed time from time zero of the first event to time zero of the second event.

Time, maximum delta-V, lateral means the time from crash time zero to the point where the maximum value of the cumulative change in velocity is found, as recorded by the EDR, along the lateral axis.

Time, maximum delta-V, longitudinal means the time from crash time zero to the point where the maximum value of the cumulative change in velocity is found, as recorded by the EDR, along the longitudinal axis.

Time, maximum delta-V, resultant means the time from crash time zero to the point where the maximum delta-V resultant occurs, as recorded by the EDR or processed during data download.

Time to deploy, pretensioner means the elapsed time from crash time zero to the deployment command for the safety belt pretensioner (for both driver and right front passenger).

Time to deploy, side air bag/curtain means the elapsed time from crash time zero to the deployment command for a side air bag or a side curtain/tube air bag (for both driver and right front passenger).

Time to first stage means the elapsed time between time zero and the time when the first stage of a frontal air bag is commanded to fire.

Time to n
th stage means the elapsed time from crash time zero to the deployment command for the nth stage of a frontal air bag (for both driver and right front passenger).

Time zero means whichever of the following occurs first:

(1) For systems with “wake-up” air bag control systems, the time at which the occupant restraint control algorithm is activated; or

(2) For continuously running algorithms,

(i) The first point in the interval where a longitudinal cumulative delta-V of over 0.8 km/h (0.5 mph) is reached within a 20 ms time period; or

(ii) For vehicles that record “delta-V, lateral,” the first point in the interval where a lateral cumulative delta-V of over 0.8 km/h (0.5 mph) is reached within a 5 ms time period; or

(3) Deployment of a non-reversible deployable restraint.

Trigger threshold means a change in vehicle velocity, in the longitudinal direction, that equals or exceeds 8 km/h within a 150 ms interval. For vehicles that record “delta-V, lateral,” trigger threshold means a change in vehicle velocity in either the longitudinal or lateral direction that equals or exceeds 8 km/h within a 150 ms interval.

Vehicle roll angle means the angle between the vehicle's y-axis and the ground plane.

Volatile memory means the memory reserved for buffering of captured EDR data. The memory is not capable of retaining data in a semi-permanent fashion. Data captured in volatile memory is continuously overwritten and is not retained in the event of a power loss or retrievable with EDR data extraction tools.

X-direction means in the direction of the vehicle's X-axis, which is parallel to the vehicle's longitudinal centerline. The X-direction is positive in the direction of forward vehicle travel.

Y-direction means in the direction of the vehicle's Y-axis, which is perpendicular to its X-axis and in the same horizontal plane as that axis. The Y-direction is positive from left to right, from the perspective of the driver when seated in the vehicle facing the direction of forward vehicle travel.

Z-direction means in the direction of the vehicle's Z-axis, which is perpendicular to the X- and Y-axes. The Z-direction is positive in a downward direction.

*[73 FR 2180, Jan. 14, 2008, as amended at 76 FR 47486, Aug. 5, 2011; 89 FR 102832, Dec. 18, 2024]*

### § 563.6 Requirements for vehicles.

Each vehicle equipped with an EDR must meet the requirements specified in § 563.7 for data elements, § 563.8 for data format, § 563.9 for data capture, § 563.10 for crash test performance and survivability, and § 563.11 for information in owner's manual.

### § 563.7 Data elements.

(a) Data elements required for all vehicles. Each vehicle equipped with an EDR must record all of the data elements listed in table I to § 563.7(a), during the interval/time and at the sample rate specified in that table.

[Table — see source for details]

(b) Data elements required for vehicles under specified conditions. Each vehicle equipped with an EDR must record each of the data elements listed in column 1 of table II to § 563.7(b) for which the vehicle meets the condition specified in column 2 of that table, during the interval/time and at the sample rate specified in that table.

[Table — see source for details]

*[89 FR 102832, Dec. 18, 2024]*

### § 563.8 Data format.

(a) The data elements listed in Tables I and II, as applicable, must be reported in accordance with the range, accuracy, and resolution specified in Table III.

[Table — see source for details]

(b) Acceleration Time-History data and format: the longitudinal, lateral, and normal acceleration time-history data, as applicable, must be filtered either during the recording phase or during the data downloading phase to include:

(1) The Time Step (TS) that is the inverse of the sampling frequency of the acceleration data and which has units of seconds;

(2) The number of the first point (NFP), which is an integer that when multiplied by the TS equals the time relative to time zero of the first acceleration data point;

(3) The number of the last point (NLP), which is an integer that when multiplied by the TS equals the time relative to time zero of the last acceleration data point; and

(4) NLP—NFP + 1 acceleration values sequentially beginning with the acceleration at time NFP * TS and continue sampling the acceleration at TS increments in time until the time NLP * TS is reached.

*[73 FR 2183, Jan. 14, 2008, as amended at 76 FR 47488, Aug. 5, 2011; 77 FR 47556, Aug. 9, 2012; 77 FR 59566, Sept. 28, 2012]*

### § 563.9 Data capture.

The EDR must capture and record the data elements for events in accordance with the following conditions and circumstances:

(a) In a frontal air bag deployment crash, capture and record the current deployment data. In a side or side curtain/tube air bag deployment crash, where lateral delta-V is recorded by the EDR, capture and record the current deployment data. The memory for the air bag deployment event must be locked to prevent any future overwriting of the data.

(b) In an event that does not meet the criteria in § 563.9(a), capture and record the current event data, up to two events, subject to the following conditions:

(1) If an EDR non-volatile memory buffer void of previous-event data is available, the current event data is recorded in the buffer.

(2) If an EDR non-volatile memory buffer void of previous-event data is not available, the manufacturer may choose to either overwrite any previous event data that does not deploy an air bag with the current event data, or to not record the current event data.

(3) EDR buffers containing previous frontal, side, or side curtain/tube air bag deployment-event data must not be overwritten by the current event data.

*[76 FR 47489, Aug. 5, 2011]*

### § 563.10 Crash test performance and survivability.

(a) Each vehicle subject to the requirements of S5, S14.5, S15, or S17 of 49 CFR 571.208, Occupant crash protection, must comply with the requirements in subpart (c) of this section when tested according to S8, S16, and S18 of 49 CFR 571.208.

(b) Each vehicle subject to the requirements of 49 CFR 571.214, Side impact protection, that meets a trigger threshold or has a frontal air bag deployment, must comply with the requirements of subpart (c) of this section when tested according to the conditions specified in 49 CFR 571.214 for a moving deformable barrier test.

(c) The data elements required by § 563.7, except for the “Engine throttle, percent full,” “engine RPM,” and “service brake, on/off,” must be recorded in the format specified by § 563.8, exist at the completion of the crash test, and be retrievable by the methodology specified by the vehicle manufacturer under § 563.12 for not less than 10 days after the test, and the complete data recorded element must read “yes” after the test.

### § 563.11 Information in owner's manual.

(a) The owner's manual in each vehicle covered under this regulation must provide the following statement in English:

This vehicle is equipped with an event data recorder (EDR). The main purpose of an EDR is to record, in certain crash or near crash-like situations, such as an air bag deployment or hitting a road obstacle, data that will assist in understanding how a vehicle's systems performed. The EDR is designed to record data related to vehicle dynamics and safety systems for a short period of time, typically 30 seconds or less. The EDR in this vehicle is designed to record such data as:

• How various systems in your vehicle were operating;

• Whether or not the driver and passenger safety belts were buckled/fastened;

• How far (if at all) the driver was depressing the accelerator and/or brake pedal; and,

• How fast the vehicle was traveling.

These data can help provide a better understanding of the circumstances in which crashes and injuries occur. NOTE: EDR data are recorded by your vehicle only if a non-trivial crash situation occurs; no data are recorded by the EDR under normal driving conditions and no personal data (e.g., name, gender, age, and crash location) are recorded. However, other parties, such as law enforcement, could combine the EDR data with the type of personally identifying data routinely acquired during a crash investigation.

To read data recorded by an EDR, special equipment is required, and access to the vehicle or the EDR is needed. In addition to the vehicle manufacturer, other parties, such as law enforcement, that have the special equipment, can read the information if they have access to the vehicle or the EDR.

(b) The owner's manual may include additional information about the form, function, and capabilities of the EDR, in supplement to the required statement in § 563.11(a).

### § 563.12 Data retrieval tools.

Each manufacturer of a motor vehicle equipped with an EDR shall ensure by licensing agreement or other means that a tool(s) is commercially available that is capable of accessing and retrieving the data stored in the EDR that are required by this part. The tool(s) shall be commercially available not later than 90 days after the first sale of the motor vehicle for purposes other than resale.