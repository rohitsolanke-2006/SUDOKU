from typing import List, Dict, Any
from app.models.schemas import SignalModel, HardwarePositionModel, RuleModel, TechnicalQuery, ProjectModel

def get_default_project() -> ProjectModel:
    return ProjectModel(
        id="proj_deltav_01",
        name="Plant Expansion — Process Unit A",
        client="Emerson Process Management — DeltaV Marshaling",
        active_revision="REV_A",
        description="Emerson DeltaV Electronic Marshaling Cabinet CAB-01 with CIOC controllers, CHARM baseplates, and field multicores.",
        created_at="2026-10-15T08:00:00Z",
        updated_at="2026-10-15T10:30:00Z"
    )

def get_default_hardware() -> List[HardwarePositionModel]:
    positions: List[HardwarePositionModel] = []
    
    # 4 Baseplates, 16 slots each = 64 slots total
    baseplate_configs = [
        {
            "id": "BP-01",
            "name": "Baseplate 01 — Standard Analog In",
            "type": "AI 4-20mA HART",
            "rail": 1,
            "supported": ["AI_HART", "AO_HART"],
            "is_is_rated": False,
            "terminal_prefix": "TB-BP01"
        },
        {
            "id": "BP-02",
            "name": "Baseplate 02 — Intrinsic Safety Barrier",
            "type": "HART / IS Barrier",
            "rail": 1,
            "supported": ["IS_AI_HART", "IS_DI_NAMUR", "AI_HART"],
            "is_is_rated": True,
            "terminal_prefix": "TB-BP02-IS"
        },
        {
            "id": "BP-03",
            "name": "Baseplate 03 — RTD / TC Temperature",
            "type": "RTD / TC Temperature",
            "rail": 2,
            "supported": ["RTD_PT100", "TC_TYPE_K"],
            "is_is_rated": False,
            "terminal_prefix": "TB-BP03"
        },
        {
            "id": "BP-04",
            "name": "Baseplate 04 — Discrete 24VDC",
            "type": "DI / DO 24VDC Discrete",
            "rail": 2,
            "supported": ["DI_24V", "DO_24V"],
            "is_is_rated": False,
            "terminal_prefix": "TB-BP04"
        }
    ]

    for bp in baseplate_configs:
        for slot in range(1, 17):
            pos_id = f"{bp['id']}-CH-{str(slot).zfill(2)}"
            # Slot 15 and 16 reserved for spare expansion by default
            is_res = (slot >= 15)
            positions.append(
                HardwarePositionModel(
                    id=pos_id,
                    cabinet_id="CAB-01",
                    cioc_id="CIOC-01" if bp["rail"] == 1 else "CIOC-02",
                    rail_id=bp["rail"],
                    baseplate_id=bp["id"],
                    slot_number=slot,
                    baseplate_type=bp["type"],
                    supported_signal_types=bp["supported"],
                    max_channels=1,
                    is_is_rated=bp["is_is_rated"],
                    is_reserved=is_res,
                    thermal_rating_watts=1.5,
                    terminal_block=f"{bp['terminal_prefix']} Term {slot*2-1}/{slot*2}",
                    status="RESERVED" if is_res else "AVAILABLE"
                )
            )
            
    return positions

def get_default_rules() -> List[RuleModel]:
    return [
        RuleModel(
            id="RULE-HARD-01",
            name="Hardware Signal Type Compatibility",
            description="A signal may only be placed in a hardware slot that explicitly supports its physical signal type (e.g., RTD signals require RTD CHARMs).",
            category="HARD",
            enabled=True,
            weight=100.0,
            parameters={},
            source="Emerson DeltaV CHARMs Hardware Installation Manual Section 3.1"
        ),
        RuleModel(
            id="RULE-HARD-02",
            name="Slot Capacity Limit",
            description="Each physical terminal block/CHARM slot can hold at most 1 primary instrument loop.",
            category="HARD",
            enabled=True,
            weight=100.0,
            parameters={"max_channels": 1},
            source="IEC 61131-2 Industrial Control Equipment Standard"
        ),
        RuleModel(
            id="RULE-HARD-03",
            name="Intrinsic Safety (Ex-ia) Segregation",
            description="Signals marked as Intrinsic Safety (Zone 0/1 hazardous areas) MUST be placed on an IS Barrier baseplate (BP-02).",
            category="HARD",
            enabled=True,
            weight=100.0,
            parameters={"required_baseplate_for_is": "BP-02"},
            source="IEC 60079-11 Explosive Atmospheres — Equipment protection by intrinsic safety 'i'"
        ),
        RuleModel(
            id="RULE-HARD-04",
            name="Voltage & Carrier Segregation",
            description="Discrete 24VDC and AC signals must not be mapped to low-level millivolt temperature or sensitive RTD baseplates.",
            category="HARD",
            enabled=True,
            weight=100.0,
            parameters={"isolated_types": ["DI_24V", "DO_24V"]},
            source="IEEE 518 Guide for the Installation of Electrical Equipment to Minimize Electrical Noise"
        ),
        RuleModel(
            id="RULE-HARD-05",
            name="Reserved Spare Position Protection",
            description="Slots designated as engineering spare reserve cannot be allocated unless explicitly released.",
            category="HARD",
            enabled=True,
            weight=100.0,
            parameters={},
            source="Project Marshaling Philosophy Doc Sec 7"
        ),
        RuleModel(
            id="RULE-SOFT-01",
            name="Revision Churn Minimization (Pin Retention)",
            description="Preserve existing valid assignments from earlier project revisions to eliminate physical cabinet rewiring costs.",
            category="SOFT",
            enabled=True,
            weight=15.0,
            parameters={"reassignment_penalty": 15},
            source="Emerson Project Lifecycle & Churn Control Methodology"
        ),
        RuleModel(
            id="RULE-SOFT-02",
            name="Multicore Cable Pair Proximity Grouping",
            description="Signals belonging to the same field multicore trunk cable should be placed in adjacent slots on the same baseplate.",
            category="SOFT",
            enabled=True,
            weight=4.0,
            parameters={"proximity_bonus": 4},
            source="API RP 552 Wire and Cable Routing Practices"
        ),
        RuleModel(
            id="RULE-SOFT-03",
            name="Thermal Load Distribution",
            description="Evenly distribute high-dissipation transmitter loops across baseplates to prevent localized heat buildup.",
            category="SOFT",
            enabled=True,
            weight=2.0,
            parameters={"max_baseplate_watts": 12.0},
            source="Rittal Enclosure Thermal Management Guidelines"
        )
    ]

def get_demo_signals_rev_a() -> List[SignalModel]:
    signals: List[SignalModel] = []
    
    # 1. Baseplate 1 AI Standard Signals (12 signals for BP-01)
    ai_specs = [
        ("SIG-PT-101", "PT-101", "Deethanizer Reboiler Pressure Transmitter", "AI_HART", "CBL-101A", 1, 0.85, "BP-01-CH-01"),
        ("SIG-PT-102", "PT-102", "Separator Column Head Pressure", "AI_HART", "CBL-101A", 2, 0.80, "BP-01-CH-02"),
        ("SIG-PT-103", "PT-103", "Boiler Drum Steam Pressure", "AI_HART", "CBL-101A", 3, 0.80, "BP-01-CH-03"),
        ("SIG-LT-201", "LT-201", "Deethanizer Bottom Liquid Level", "AI_HART", "CBL-101A", 4, 0.75, "BP-01-CH-04"),
        ("SIG-LT-202", "LT-202", "Reflux Drum Liquid Level", "AI_HART", "CBL-102A", 1, 0.75, "BP-01-CH-05"),
        ("SIG-FT-301", "FT-301", "Crude Feed Orifice Flowmeter", "AI_HART", "CBL-102A", 2, 0.90, "BP-01-CH-06"),
        ("SIG-FT-302", "FT-302", "Reflux Line Flow Transmitter", "AI_HART", "CBL-102A", 3, 0.90, "BP-01-CH-07"),
        ("SIG-FT-303", "FT-303", "Steam Header Mass Flowmeter", "AI_HART", "CBL-102A", 4, 0.90, "BP-01-CH-08"),
        ("SIG-AO-101", "FV-101", "Reflux Control Valve Positioner AO", "AO_HART", "CBL-103A", 1, 0.95, "BP-01-CH-09"),
        ("SIG-AO-102", "PV-102", "Steam Bypass Valve Positioner AO", "AO_HART", "CBL-103A", 2, 0.95, "BP-01-CH-10"),
        ("SIG-AO-103", "LV-201", "Bottoms Drain Control Valve AO", "AO_HART", "CBL-103A", 3, 0.95, "BP-01-CH-11"),
        ("SIG-PT-104", "PT-104", "Cooling Water Return Pressure", "AI_HART", "CBL-103A", 4, 0.75, "BP-01-CH-12"),
    ]
    for s_id, tag, desc, st, cbl, pair, pwr, pos in ai_specs:
        signals.append(
            SignalModel(
                id=s_id,
                tag=tag,
                description=desc,
                signal_type=st,
                voltage="24VDC",
                is_intrinsic_safety=False,
                safety_integrity_level="BPCS",
                multicore_cable_id=cbl,
                cable_pair_index=pair,
                power_dissipation_watts=pwr,
                assigned_position_id=pos,
                locked=False,
                revision="REV_A",
                status="ALLOCATED"
            )
        )

    # 2. Baseplate 2 Intrinsic Safety Signals (10 signals for BP-02)
    is_specs = [
        ("SIG-IS-PT-105", "PT-105-IS", "Reactor Flare Header Pressure [Zone 0 Ex-ia]", "IS_AI_HART", "CBL-201A", 1, 0.85, "BP-02-CH-01"),
        ("SIG-IS-PT-106", "PT-106-IS", "Hydrogen Purge Header Pressure [Zone 0 Ex-ia]", "IS_AI_HART", "CBL-201A", 2, 0.85, "BP-02-CH-02"),
        ("SIG-IS-FT-104B", "FT-104B", "Backup Boiler Feedwater Flow Transmitter [Zone 1]", "IS_AI_HART", "CBL-201A", 3, 0.90, "BP-02-CH-03"),
        ("SIG-IS-LT-205", "LT-205-IS", "Hydrocarbon Slop Tank Level [Zone 1 Ex-ia]", "IS_AI_HART", "CBL-201A", 4, 0.80, "BP-02-CH-04"),
        ("SIG-IS-PT-107", "PT-107-IS", "Polymer Flash Vessel Pressure [Zone 0 Ex-ia]", "IS_AI_HART", "CBL-202A", 1, 0.85, "BP-02-CH-05"),
        ("SIG-IS-ZT-201", "ZS-201-IS", "Emergency Blowdown Valve Position Switch [Ex-ia]", "IS_DI_NAMUR", "CBL-202A", 2, 0.45, "BP-02-CH-06"),
        ("SIG-IS-ZT-202", "ZS-202-IS", "Reactor Rupture Disc Rupture Indicator [Ex-ia]", "IS_DI_NAMUR", "CBL-202A", 3, 0.45, "BP-02-CH-07"),
        ("SIG-IS-PT-108", "PT-108-IS", "Vent Header Pressure Transmitter [Zone 1]", "IS_AI_HART", "CBL-202A", 4, 0.85, "BP-02-CH-08"),
        ("SIG-IS-ZT-203", "ZS-203-IS", "Hydrocarbon Spill Sump High Level [Ex-ia]", "IS_DI_NAMUR", "CBL-203A", 1, 0.45, "BP-02-CH-09"),
        ("SIG-IS-ZT-204", "ZS-204-IS", "Vapor Recovery Unit Status [Ex-ia]", "IS_DI_NAMUR", "CBL-203A", 2, 0.45, "BP-02-CH-10"),
    ]
    for s_id, tag, desc, st, cbl, pair, pwr, pos in is_specs:
        signals.append(
            SignalModel(
                id=s_id,
                tag=tag,
                description=desc,
                signal_type=st,
                voltage="24VDC",
                is_intrinsic_safety=True,
                safety_integrity_level="SIL-2",
                multicore_cable_id=cbl,
                cable_pair_index=pair,
                power_dissipation_watts=pwr,
                assigned_position_id=pos,
                locked=True if tag == "PT-105-IS" else False,
                revision="REV_A",
                status="ALLOCATED"
            )
        )

    # 3. Baseplate 3 RTD / TC Temperature Signals (11 signals for BP-03)
    temp_specs = [
        ("SIG-TT-401", "TT-401", "Turbine Bearing A Temperature Pt100", "RTD_PT100", "CBL-301A", 1, 0.35, "BP-03-CH-01"),
        ("SIG-TT-402", "TT-402", "Turbine Bearing B Temperature Pt100", "RTD_PT100", "CBL-301A", 2, 0.35, "BP-03-CH-02"),
        ("SIG-TT-403", "TT-403", "Compressor Thrust Bearing Temperature", "RTD_PT100", "CBL-301A", 3, 0.35, "BP-03-CH-03"),
        ("SIG-TT-204", "TT-204", "Compressor Casing Temperature Sensor", "RTD_PT100", "CBL-301A", 4, 0.35, "BP-03-CH-04"),
        ("SIG-TE-501", "TE-501", "Furnace Firebox Top Temp Thermocouple K", "TC_TYPE_K", "CBL-302A", 1, 0.25, "BP-03-CH-05"),
        ("SIG-TE-502", "TE-502", "Furnace Radiant Tube Wall Temperature", "TC_TYPE_K", "CBL-302A", 2, 0.25, "BP-03-CH-06"),
        ("SIG-TE-503", "TE-503", "Convection Section Flue Gas Temperature", "TC_TYPE_K", "CBL-302A", 3, 0.25, "BP-03-CH-07"),
        ("SIG-TT-404", "TT-404", "Cooling Water Return Temperature Pt100", "RTD_PT100", "CBL-302A", 4, 0.35, "BP-03-CH-08"),
        ("SIG-TT-405", "TT-405", "Lube Oil Sump Temperature Pt100", "RTD_PT100", "CBL-303A", 1, 0.35, "BP-03-CH-09"),
        ("SIG-TE-504", "TE-504", "Stack Flue Gas Emission Temperature", "TC_TYPE_K", "CBL-303A", 2, 0.25, "BP-03-CH-10"),
        ("SIG-TT-406", "TT-406", "Intercooler Outlet Gas Temp Pt100", "RTD_PT100", "CBL-303A", 3, 0.35, "BP-03-CH-11"),
    ]
    for s_id, tag, desc, st, cbl, pair, pwr, pos in temp_specs:
        signals.append(
            SignalModel(
                id=s_id,
                tag=tag,
                description=desc,
                signal_type=st,
                voltage="mV",
                is_intrinsic_safety=False,
                safety_integrity_level="BPCS",
                multicore_cable_id=cbl,
                cable_pair_index=pair,
                power_dissipation_watts=pwr,
                assigned_position_id=pos,
                locked=False,
                revision="REV_A",
                status="ALLOCATED"
            )
        )

    # 4. Baseplate 4 Discrete 24VDC Signals (12 signals for BP-04)
    disc_specs = [
        ("SIG-LSH-101", "LSH-101", "Deethanizer Reboiler High Level Alarm Switch", "DI_24V", "CBL-401A", 1, 0.50, "BP-04-CH-01"),
        ("SIG-LSL-101", "LSL-101", "Deethanizer Reboiler Low Level Alarm Switch", "DI_24V", "CBL-401A", 2, 0.50, "BP-04-CH-02"),
        ("SIG-ZSO-201", "ZSO-201", "ESD Feed Isolation Valve Open Limit Switch", "DI_24V", "CBL-401A", 3, 0.50, "BP-04-CH-03"),
        ("SIG-ZSC-201", "ZSC-201", "ESD Feed Isolation Valve Closed Limit Switch", "DI_24V", "CBL-401A", 4, 0.50, "BP-04-CH-04"),
        ("SIG-SOV-101", "SOV-101", "ESD Emergency Feed Isolation Solenoid Valve", "DO_24V", "CBL-402A", 1, 1.20, "BP-04-CH-05"),
        ("SIG-SOV-102", "SOV-102", "Fuel Gas Emergency Vent Solenoid Valve", "DO_24V", "CBL-402A", 2, 1.20, "BP-04-CH-06"),
        ("SIG-PMP-RUN", "PMP-RUN-01", "Reflux Pump Motor Running Feedback Contact", "DI_24V", "CBL-402A", 3, 0.50, "BP-04-CH-07"),
        ("SIG-PMP-CMD", "PMP-CMD-01", "Reflux Pump Motor Remote Start Command DO", "DO_24V", "CBL-402A", 4, 1.10, "BP-04-CH-08"),
        ("SIG-ALM-HRN", "ALM-HORN-01", "Control Room Audible Annunciator Horn DO", "DO_24V", "CBL-403A", 1, 1.10, "BP-04-CH-09"),
        ("SIG-ALM-STR", "ALM-STROBE-01","Field Evacuation Strobe Beacon DO", "DO_24V", "CBL-403A", 2, 1.10, "BP-04-CH-10"),
        ("SIG-ESD-PB1", "ESD-PB-01", "Field Console Emergency Shutdown Pushbutton", "DI_24V", "CBL-403A", 3, 0.50, "BP-04-CH-11"),
        ("SIG-ESD-RST", "ESD-RESET-01","Field Safety Interlock Permissive Reset DI", "DI_24V", "CBL-403A", 4, 0.50, "BP-04-CH-12"),
    ]
    for s_id, tag, desc, st, cbl, pair, pwr, pos in disc_specs:
        signals.append(
            SignalModel(
                id=s_id,
                tag=tag,
                description=desc,
                signal_type=st,
                voltage="24VDC",
                is_intrinsic_safety=False,
                safety_integrity_level="SIL-3" if "ESD" in tag else "BPCS",
                multicore_cable_id=cbl,
                cable_pair_index=pair,
                power_dissipation_watts=pwr,
                assigned_position_id=pos,
                locked=True if "ESD" in tag else False,
                revision="REV_A",
                status="ALLOCATED"
            )
        )

    return signals

def get_demo_signals_rev_b() -> List[SignalModel]:
    """
    Revision B contains realistic changes:
    1. 43 preserved signals from Rev A
    2. 1 modified signal: PT-102 changed from AI_HART to IS_AI_HART (requires move to BP-02)
    3. 1 decommissioned/removed signal: TT-405 removed
    4. 5 new signals added:
       - PT-109 (AI_HART)
       - TT-409 (RTD_PT100)
       - SOV-105 (DO_24V)
       - ZS-205-IS (IS_DI_NAMUR)
       - FT-305 (AI_HART)
    """
    rev_a = get_demo_signals_rev_a()
    rev_b_signals: List[SignalModel] = []
    
    for s in rev_a:
        if s.id == "SIG-TT-405":
            # Decommissioned in Rev B - omitted!
            continue
        elif s.id == "SIG-PT-102":
            # Modified in Rev B: now requires Intrinsic Safety (IS_AI_HART)
            rev_b_signals.append(
                SignalModel(
                    id=s.id,
                    tag=s.tag,
                    description=s.description + " [Upgraded to Ex-ia IS]",
                    signal_type="IS_AI_HART",
                    voltage="24VDC",
                    is_intrinsic_safety=True,
                    safety_integrity_level="SIL-2",
                    multicore_cable_id="CBL-201A",
                    cable_pair_index=5,
                    power_dissipation_watts=0.85,
                    assigned_position_id=None,  # Reset for solver to optimize
                    locked=False,
                    revision="REV_B",
                    status="UNALLOCATED"
                )
            )
        else:
            # Preserved signal with original assignment
            rev_b_signals.append(
                SignalModel(
                    id=s.id,
                    tag=s.tag,
                    description=s.description,
                    signal_type=s.signal_type,
                    voltage=s.voltage,
                    is_intrinsic_safety=s.is_intrinsic_safety,
                    safety_integrity_level=s.safety_integrity_level,
                    redundancy=s.redundancy,
                    multicore_cable_id=s.multicore_cable_id,
                    cable_pair_index=s.cable_pair_index,
                    power_dissipation_watts=s.power_dissipation_watts,
                    assigned_position_id=s.assigned_position_id,
                    locked=s.locked,
                    revision="REV_B",
                    status="ALLOCATED"
                )
            )
            
    # Add new signals in Rev B
    new_additions = [
        SignalModel(
            id="SIG-PT-109",
            tag="PT-109",
            description="Flare Gas Recovery Drum Suction Pressure",
            signal_type="AI_HART",
            voltage="24VDC",
            is_intrinsic_safety=False,
            safety_integrity_level="BPCS",
            multicore_cable_id="CBL-103A",
            cable_pair_index=5,
            power_dissipation_watts=0.80,
            assigned_position_id=None,
            locked=False,
            revision="REV_B",
            status="UNALLOCATED"
        ),
        SignalModel(
            id="SIG-TT-409",
            tag="TT-409",
            description="Compressor Motor Stator Winding Phase U Temp",
            signal_type="RTD_PT100",
            voltage="mV",
            is_intrinsic_safety=False,
            safety_integrity_level="BPCS",
            multicore_cable_id="CBL-303A",
            cable_pair_index=4,
            power_dissipation_watts=0.35,
            assigned_position_id=None,
            locked=False,
            revision="REV_B",
            status="UNALLOCATED"
        ),
        SignalModel(
            id="SIG-SOV-105",
            tag="SOV-105",
            description="Flare Knockout Drum Nitrogen Purge Solenoid DO",
            signal_type="DO_24V",
            voltage="24VDC",
            safety_integrity_level="SIL-2",
            multicore_cable_id="CBL-403A",
            cable_pair_index=5,
            power_dissipation_watts=1.15,
            assigned_position_id=None,
            locked=False,
            revision="REV_B",
            status="UNALLOCATED"
        ),
        SignalModel(
            id="SIG-IS-ZS-205",
            tag="ZS-205-IS",
            description="Solvent Recovery Tank Emergency Vent Hatch [Zone 0]",
            signal_type="IS_DI_NAMUR",
            voltage="24VDC",
            is_intrinsic_safety=True,
            safety_integrity_level="SIL-2",
            multicore_cable_id="CBL-203A",
            cable_pair_index=3,
            power_dissipation_watts=0.45,
            assigned_position_id=None,
            locked=False,
            revision="REV_B",
            status="UNALLOCATED"
        ),
        SignalModel(
            id="SIG-FT-305",
            tag="FT-305",
            description="Demineralized Water Flush Line Coriolis Meter",
            signal_type="AI_HART",
            voltage="24VDC",
            is_intrinsic_safety=False,
            safety_integrity_level="BPCS",
            multicore_cable_id="CBL-102A",
            cable_pair_index=5,
            power_dissipation_watts=0.85,
            assigned_position_id=None,
            locked=False,
            revision="REV_B",
            status="UNALLOCATED"
        )
    ]
    rev_b_signals.extend(new_additions)
    return rev_b_signals

def get_demo_tqs() -> List[TechnicalQuery]:
    return [
        TechnicalQuery(
            id="TQ-001",
            title="Ex-ia Intrinsic Safety Barrier Capacity Alert on BP-02",
            signal_id="SIG-PT-102",
            position_id="BP-02-CH-11",
            category="IS_SEGREGATION",
            severity="WARNING",
            status="UNDER_REVIEW",
            assignee="H. Chen (Senior Electrical Safety Engineer)",
            description="Process change notice ECO-482 upgrades Separator Column Head Pressure PT-102 to Zone 0 Ex-ia classification. Baseplate BP-02 currently has 10 active IS loops and 4 unassigned slots, but slots 15-16 are marked as project spares. Need confirmation whether slot BP-02-CH-11 can be allocated without violating future expansion reserves.",
            suggested_resolution="Allocate to BP-02-CH-11 as proposed by solver; spare margin remains at 33% (4 available slots).",
            created_at="2026-10-15T09:15:00Z",
            updated_at="2026-10-15T11:00:00Z",
            comments=[
                {"author": "H. Chen", "timestamp": "2026-10-15T09:30:00Z", "text": "Calculation verified: BP-02 total galvanic isolation barrier load is 8.9W, within the 12W enclosure thermal limit."},
                {"author": "J. Vance", "timestamp": "2026-10-15T10:45:00Z", "text": "Approved pending baseline acceptance."}
            ]
        ),
        TechnicalQuery(
            id="TQ-002",
            title="ESD Feed Isolation Pushbutton Redundancy Verification",
            signal_id="SIG-ESD-PB1",
            position_id="BP-04-CH-11",
            category="TYPE_INCOMPATIBILITY",
            severity="INFO",
            status="RESOLVED",
            assignee="M. Al-Sayed (Lead Safety Systems Engineer)",
            description="Confirm SIL-3 Emergency Shutdown button loop monitoring resistor configuration on DeltaV DI 24VDC CHARM terminal block.",
            suggested_resolution="Standard Emerson DeltaV DI CHARM with line-fault detection resistor pack installed at field junction box.",
            created_at="2026-10-14T14:00:00Z",
            updated_at="2026-10-15T08:20:00Z",
            comments=[
                {"author": "M. Al-Sayed", "timestamp": "2026-10-15T08:20:00Z", "text": "Confirmed with Emerson FAT specification sheet rev 3."}
            ]
        )
    ]

def get_scenario_b_signals() -> List[SignalModel]:
    """
    Scenario B: Controlled Engineering Constraint Conflict.
    Includes an intentional Intrinsic Safety violation:
    Hazardous Zone 0 loop PT-FLARE-IS is locked to standard non-IS slot BP-01-CH-01.
    Because BP-01 lacks galvanic isolation, the solver detects INFEASIBILITY
    and diagnostics isolates RULE-HARD-03 (IEC 60079-11) as the exact culprit.
    """
    signals = get_demo_signals_rev_a()
    
    # Insert conflicting signal
    conflict_signal = SignalModel(
        id="SIG-CONFLICT-IS-01",
        tag="PT-FLARE-IS",
        description="Flare Stack Toxic Gas Purge Pressure [Hazardous Zone 0 Ex-ia]",
        signal_type="IS_AI_HART",
        voltage="24VDC",
        is_intrinsic_safety=True,
        safety_integrity_level="SIL-3",
        multicore_cable_id="CBL-999-HAZ",
        cable_pair_index=1,
        power_dissipation_watts=0.85,
        assigned_position_id="BP-01-CH-01",  # LOCKED TO STANDARD NON-IS BASEPLATE!
        locked=True,
        revision="REV_A",
        status="CONFLICT"
    )
    # Put conflict signal at the front so it is immediately prominent
    signals.insert(0, conflict_signal)
    return signals

def get_scenario_b_tqs() -> List[TechnicalQuery]:
    tqs = get_demo_tqs()
    conflict_tq = TechnicalQuery(
        id="TQ-003",
        title="CRITICAL: Hazardous Zone 0 Signal Locked to Non-IS Standard Baseplate BP-01",
        signal_id="SIG-CONFLICT-IS-01",
        position_id="BP-01-CH-01",
        category="IS_SEGREGATION",
        severity="CRITICAL",
        status="OPEN",
        assignee="Lead Safety Systems Engineer",
        description="Safety Audit Failure: Loop PT-FLARE-IS is marked as Zone 0 Ex-ia Intrinsic Safety but locked by field engineer to slot BP-01-CH-01. Baseplate BP-01 is standard 4-20mA HART without galvanic barrier protection (IEC 60079-11 violation). Solver cannot produce feasible schedule until barrier position is assigned.",
        suggested_resolution="Unlock loop or reassign to certified Intrinsic Safety barrier baseplate BP-02.",
        created_at="2026-10-16T14:30:00Z",
        updated_at="2026-10-16T14:30:00Z",
        comments=[
            {"author": "System Auditor", "timestamp": "2026-10-16T14:30:00Z", "text": "Automatic parity check flagged RULE-HARD-03 conflict."}
        ]
    )
    tqs.insert(0, conflict_tq)
    return tqs

SCENARIOS_CATALOG = {
    "SCENARIO_A": {
        "id": "SCENARIO_A",
        "name": "Scenario A — Clean Allocation",
        "badge": "SUCCESS PATH",
        "badge_color": "valid",
        "description": "Baseline instrumentation register (45 loops: AI, AO, IS, RTD, TC, DI, DO). Demonstrates end-to-end OR-Tools CP-SAT solving, 100% capacity and compatibility satisfaction, and 0 hard violations.",
        "expected_status": "OPTIMAL",
        "signals_count": 45,
        "revision": "REV_A"
    },
    "SCENARIO_B": {
        "id": "SCENARIO_B",
        "name": "Scenario B — Constraint Conflict",
        "badge": "FAILURE AUDIT",
        "badge_color": "error",
        "description": "Controlled safety violation: Hazardous Zone 0 loop PT-FLARE-IS locked to standard non-IS slot BP-01-CH-01. Demonstrates CP-SAT infeasibility detection, candidate elimination diagnostics, and automatic TQ issue generation.",
        "expected_status": "INFEASIBLE",
        "signals_count": 46,
        "revision": "REV_A"
    },
    "SCENARIO_C": {
        "id": "SCENARIO_C",
        "name": "Scenario C — Revision Churn Minimizer",
        "badge": "WHAT-IF SIMULATOR",
        "badge_color": "brand",
        "description": "Rev A baseline (45 loops) vs Rev B engineering change order (49 loops: +5 additions, -1 deletion, PT-102 upgraded to Ex-ia). Demonstrates warm-start L1 pin retention, preserving 97.7% of field terminations and saving 64.5 man-hours.",
        "expected_status": "OPTIMAL (MINIMAL CHURN)",
        "signals_count": 49,
        "revision": "REV_B"
    }
}

