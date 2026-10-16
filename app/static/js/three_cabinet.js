/**
 * IO SIGNAL SUDOKU — Interactive 3D Digital Twin Cabinet Engine
 * Three.js Modular Industrial Substation Environment & Rittal TS8 / Emerson DeltaV Marshaling Enclosure
 * 
 * Features:
 * - Industrial Control Room Environment: Epoxy substation floor with hazard border, back wall, cable tray, luminaire fixtures
 * - Open Cabinet Doors: Twin hinged steel doors with tinted acrylic window, gasket, and chrome latch handle
 * - Emerson DeltaV Marshaling Hardware: Dual CIOC controllers, 4 Baseplates, 64 CHARM slots with status LEDs
 * - High-Contrast Readable Labels: Baseplate title plaques, channel numbers, and dynamic signal tags
 * - Interactive Wire Routing: Animated 3D CatmullRom cable spline tracing from entry gland to terminal screws
 * - Raycasting & Two-Way Sync: Click slot to inspect in table and HUD; hover tooltips
 * - Accessible Status Indicators: Multi-modal (Text + Icon + Color)
 * - Camera Presets & Smooth Controls: Orbit, Pan, Zoom, Fit-to-Cabinet, Reset
 */

class Cabinet3DViewer {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container #${containerId} not found.`);
      return;
    }

    this.onSelectCallback = options.onSelect || (() => {});
    this.slots = new Map(); // slotId -> metadata
    this.selectedSlotId = null;
    this.hoveredSlotId = null;
    this.activeFilter = 'ALL';
    this.wireMesh = null;

    this.initScene();
    this.buildIndustrialEnvironment();
    this.buildCabinetGeometry();
    this.setupInteractions();
    this.setupTooltip();
    this.animate();
  }

  initScene() {
    this.width = this.container.clientWidth || 800;
    this.height = this.container.clientHeight || 600;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x161c1b); // Deep slate industrial room ambience
    this.scene.fog = new THREE.FogExp2(0x161c1b, 0.045);

    // Camera setup
    this.camera = new THREE.PerspectiveCamera(36, this.width / this.height, 0.1, 100);
    this.initialSpherical = { radius: 6.4, theta: 0.42, phi: 1.25 };
    this.initialLookAt = new THREE.Vector3(0, 0.05, 0);

    this.spherical = { ...this.initialSpherical };
    this.targetSpherical = { ...this.initialSpherical };
    this.cameraLookAt = this.initialLookAt.clone();
    this.targetLookAt = this.initialLookAt.clone();

    this.updateCameraPosition();

    // WebGL Renderer with graceful fallback
    try {
      this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    } catch (e) {
      console.warn("WebGL not available, attempting basic canvas renderer:", e);
      this.container.innerHTML = `<div class="p-6 text-center text-neutral-300 font-mono">WebGL is disabled or unsupported on this device. Use the Signal Matrix table for complete allocation controls.</div>`;
      return;
    }

    this.renderer.setSize(this.width, this.height);
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    this.container.appendChild(this.renderer.domElement);

    // Industrial Lighting System
    const ambientLight = new THREE.AmbientLight(0xdde6e3, 0.7);
    this.scene.add(ambientLight);

    // Main Overhead Industrial Key Light
    const overheadKey = new THREE.DirectionalLight(0xffffff, 1.1);
    overheadKey.position.set(2, 6, 4);
    overheadKey.castShadow = true;
    overheadKey.shadow.mapSize.width = 1024;
    overheadKey.shadow.mapSize.height = 1024;
    overheadKey.shadow.bias = -0.0003;
    this.scene.add(overheadKey);

    // Left fill light (cool cyan-tinted)
    const fillLight = new THREE.DirectionalLight(0x9bc2ba, 0.5);
    fillLight.position.set(-5, 3, -1);
    this.scene.add(fillLight);

    // Floor bounce light
    const bounceLight = new THREE.DirectionalLight(0x5a706b, 0.35);
    bounceLight.position.set(0, -4, 2);
    this.scene.add(bounceLight);

    // Materials Palette
    this.materials = {
      enclosure: new THREE.MeshStandardMaterial({ color: 0x242b29, metalness: 0.4, roughness: 0.6 }),
      enclosureDoor: new THREE.MeshStandardMaterial({ color: 0x1e2422, metalness: 0.5, roughness: 0.5 }),
      acrylicWindow: new THREE.MeshPhysicalMaterial({ color: 0x2e3b38, transparent: true, opacity: 0.35, roughness: 0.15, transmission: 0.85, thickness: 0.05 }),
      interiorBackplate: new THREE.MeshStandardMaterial({ color: 0xa2aaa5, metalness: 0.75, roughness: 0.3 }),
      galvanizedSteel: new THREE.MeshStandardMaterial({ color: 0xc8ceca, metalness: 0.85, roughness: 0.25 }),
      wireDuct: new THREE.MeshStandardMaterial({ color: 0x1d2220, roughness: 0.85, metalness: 0.15 }),
      controllerChassis: new THREE.MeshStandardMaterial({ color: 0x1c211f, roughness: 0.5, metalness: 0.4 }),
      charmCarrier: new THREE.MeshStandardMaterial({ color: 0x2e3533, roughness: 0.7, metalness: 0.2 }),
      terminalBlock: new THREE.MeshStandardMaterial({ color: 0x404946, roughness: 0.6 }),
      screwHead: new THREE.MeshStandardMaterial({ color: 0xd9dedb, metalness: 0.9, roughness: 0.2 }),
      doorHandle: new THREE.MeshStandardMaterial({ color: 0xe0e0e0, metalness: 0.95, roughness: 0.15 }),
      // CHARM status caps
      capAllocated: new THREE.MeshStandardMaterial({ color: 0x2e7d32, roughness: 0.4, metalness: 0.2 }),
      capSpare: new THREE.MeshStandardMaterial({ color: 0x546e7a, roughness: 0.5, metalness: 0.2 }),
      capWarning: new THREE.MeshStandardMaterial({ color: 0xc58a2b, roughness: 0.4, metalness: 0.3 }),
      capConflict: new THREE.MeshStandardMaterial({ color: 0xb94a48, roughness: 0.4, metalness: 0.3 }),
      capSelected: new THREE.MeshStandardMaterial({ color: 0x00bcd4, roughness: 0.3, metalness: 0.4, emissive: 0x00695c, emissiveIntensity: 0.5 }),
      capISBlue: new THREE.MeshStandardMaterial({ color: 0x1565c0, roughness: 0.4, metalness: 0.2 }),
      // Wire materials
      wireActive: new THREE.MeshStandardMaterial({ color: 0x00e5ff, emissive: 0x00838f, emissiveIntensity: 0.6, roughness: 0.3 }),
      // LEDs
      ledGreen: new THREE.MeshBasicMaterial({ color: 0x00e676 }),
      ledAmber: new THREE.MeshBasicMaterial({ color: 0xffb300 }),
      ledRed: new THREE.MeshBasicMaterial({ color: 0xff1744 }),
      ledCyan: new THREE.MeshBasicMaterial({ color: 0x00e5ff }),
      ledOff: new THREE.MeshBasicMaterial({ color: 0x37474f })
    };

    window.addEventListener('resize', () => this.onResize());
  }

  /**
   * Builds an authentic industrial substation room environment surrounding the cabinet.
   */
  buildIndustrialEnvironment() {
    this.envGroup = new THREE.Group();
    this.scene.add(this.envGroup);

    // 1. Tiled Substation Floor
    const floorCanvas = document.createElement('canvas');
    floorCanvas.width = 512;
    floorCanvas.height = 512;
    const ctx = floorCanvas.getContext('2d');
    ctx.fillStyle = '#1e2422';
    ctx.fillRect(0, 0, 512, 512);
    ctx.strokeStyle = '#293330';
    ctx.lineWidth = 2;
    for (let i = 0; i <= 512; i += 64) {
      ctx.beginPath();
      ctx.moveTo(i, 0); ctx.lineTo(i, 512);
      ctx.moveTo(0, i); ctx.lineTo(512, i);
      ctx.stroke();
    }
    const floorTexture = new THREE.CanvasTexture(floorCanvas);
    floorTexture.wrapS = THREE.RepeatWrapping;
    floorTexture.wrapT = THREE.RepeatWrapping;
    floorTexture.repeat.set(16, 16);

    const floorGeo = new THREE.PlaneGeometry(24, 24);
    const floorMat = new THREE.MeshStandardMaterial({ map: floorTexture, roughness: 0.75, metalness: 0.2 });
    const floor = new THREE.Mesh(floorGeo, floorMat);
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -1.98;
    floor.receiveShadow = true;
    this.envGroup.add(floor);

    // 2. Yellow/Black Safety Clearance Perimeter Line on Floor
    const hazardCanvas = document.createElement('canvas');
    hazardCanvas.width = 256;
    hazardCanvas.height = 32;
    const hCtx = hazardCanvas.getContext('2d');
    hCtx.fillStyle = '#ffc107';
    hCtx.fillRect(0, 0, 256, 32);
    hCtx.fillStyle = '#212121';
    for (let x = -32; x < 288; x += 32) {
      hCtx.beginPath();
      hCtx.moveTo(x, 0);
      hCtx.lineTo(x + 20, 32);
      hCtx.lineTo(x + 36, 32);
      hCtx.lineTo(x + 16, 0);
      hCtx.closePath();
      hCtx.fill();
    }
    const hazardTex = new THREE.CanvasTexture(hazardCanvas);
    hazardTex.wrapS = THREE.RepeatWrapping;
    hazardTex.repeat.set(8, 1);

    const hazardBorderGeo = new THREE.RingGeometry(1.4, 1.48, 4);
    const hazardBorderMat = new THREE.MeshBasicMaterial({ map: hazardTex, side: THREE.DoubleSide });
    const hazardBorder = new THREE.Mesh(hazardBorderGeo, hazardBorderMat);
    hazardBorder.rotation.x = -Math.PI / 2;
    hazardBorder.rotation.z = Math.PI / 4;
    hazardBorder.position.set(0, -1.97, 0.1);
    this.envGroup.add(hazardBorder);

    // 3. Control Room Back Wall
    const wallGeo = new THREE.PlaneGeometry(24, 12);
    const wallMat = new THREE.MeshStandardMaterial({ color: 0x222a28, roughness: 0.9 });
    const backWall = new THREE.Mesh(wallGeo, wallMat);
    backWall.position.set(0, 2.5, -2.8);
    backWall.receiveShadow = true;
    this.envGroup.add(backWall);

    // 4. Overhead Industrial Cable Tray (Ladder Rack)
    const trayGroup = new THREE.Group();
    trayGroup.position.set(0, 2.4, -0.6);
    // Two longitudinal side rails
    [-0.3, 0.3].forEach(z => {
      const railMesh = new THREE.Mesh(new THREE.BoxGeometry(6.0, 0.05, 0.03), this.materials.galvanizedSteel);
      railMesh.position.set(0, 0, z);
      trayGroup.add(railMesh);
    });
    // Cross rungs
    for (let rx = -2.8; rx <= 2.8; rx += 0.35) {
      const rung = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.03, 0.6), this.materials.galvanizedSteel);
      rung.position.set(rx, -0.01, 0);
      trayGroup.add(rung);
    }
    this.envGroup.add(trayGroup);

    // 5. Overhead Fluorescent Light Fixtures (Luminaires)
    [-1.2, 1.2].forEach(lx => {
      const fixtureBox = new THREE.Mesh(
        new THREE.BoxGeometry(0.24, 0.08, 1.8),
        new THREE.MeshStandardMaterial({ color: 0x1f2423, metalness: 0.6 })
      );
      fixtureBox.position.set(lx, 2.65, 0.4);
      // Bright fluorescent tube
      const tube = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.03, 1.6, 12),
        new THREE.MeshBasicMaterial({ color: 0xffffff })
      );
      tube.rotation.x = Math.PI / 2;
      tube.position.set(0, -0.04, 0);
      fixtureBox.add(tube);
      this.envGroup.add(fixtureBox);
    });
  }

  buildCabinetGeometry() {
    this.cabinetGroup = new THREE.Group();
    this.scene.add(this.cabinetGroup);

    // Enclosure Specs (Rittal TS8 / DeltaV Standard)
    const cw = 1.9, ch = 3.6, cd = 0.9;
    
    // Backplate
    const bpGeo = new THREE.BoxGeometry(cw - 0.08, ch - 0.08, 0.03);
    const backplate = new THREE.Mesh(bpGeo, this.materials.interiorBackplate);
    backplate.position.set(0, 0, -cd / 2 + 0.02);
    backplate.receiveShadow = true;
    this.cabinetGroup.add(backplate);

    // Outer Frame Walls
    const wallMat = this.materials.enclosure;
    // Top & Bottom
    const tbGeo = new THREE.BoxGeometry(cw, 0.05, cd);
    const topWall = new THREE.Mesh(tbGeo, wallMat);
    topWall.position.set(0, ch / 2, 0);
    this.cabinetGroup.add(topWall);
    const botWall = new THREE.Mesh(tbGeo, wallMat);
    botWall.position.set(0, -ch / 2, 0);
    this.cabinetGroup.add(botWall);

    // Left & Right Walls
    const lrGeo = new THREE.BoxGeometry(0.05, ch, cd);
    const leftWall = new THREE.Mesh(lrGeo, wallMat);
    leftWall.position.set(-cw / 2, 0, 0);
    this.cabinetGroup.add(leftWall);
    const rightWall = new THREE.Mesh(lrGeo, wallMat);
    rightWall.position.set(cw / 2, 0, 0);
    this.cabinetGroup.add(rightWall);

    // Cabinet Plinth / Base
    const plinthGeo = new THREE.BoxGeometry(cw + 0.04, 0.18, cd + 0.04);
    const plinth = new THREE.Mesh(plinthGeo, new THREE.MeshStandardMaterial({ color: 0x161a19, roughness: 0.9 }));
    plinth.position.set(0, -ch / 2 - 0.09, 0);
    this.cabinetGroup.add(plinth);

    // Real Open Enclosure Doors (Hinged at left and right sides)
    this.buildEnclosureDoors(cw, ch, cd);

    // Dual Emerson DeltaV CIOC Controllers
    this.buildCIOCControllers();

    // DIN Rails (Galvanized Steel)
    const railYPositions = [0.42, -0.65];
    railYPositions.forEach(y => {
      const railGeo = new THREE.BoxGeometry(1.65, 0.04, 0.015);
      const rail = new THREE.Mesh(railGeo, this.materials.galvanizedSteel);
      rail.position.set(0, y, -cd / 2 + 0.06);
      rail.castShadow = true;
      this.cabinetGroup.add(rail);
    });

    // Slotted Panduit Cable Ducts
    this.buildCableDucts();

    // 4 Baseplates with 64 CHARM Modules & Readable Text Plaques
    this.buildBaseplates();

    // Bottom Cable Entry Gland Plate
    this.buildCableGlands();
  }

  buildEnclosureDoors(cw, ch, cd) {
    // Left Door (Hinged open at ~75 degrees)
    const leftHinge = new THREE.Group();
    leftHinge.position.set(-cw / 2, 0, cd / 2);
    leftHinge.rotation.y = -1.35; // Swung open outward

    const doorW = cw / 2 - 0.02;
    const doorFrame = new THREE.Mesh(
      new THREE.BoxGeometry(doorW, ch - 0.08, 0.03),
      this.materials.enclosureDoor
    );
    doorFrame.position.set(doorW / 2, 0, 0);
    leftHinge.add(doorFrame);

    // Tinted Acrylic Inspection Window
    const winGeo = new THREE.BoxGeometry(doorW - 0.16, ch - 0.6, 0.02);
    const winMesh = new THREE.Mesh(winGeo, this.materials.acrylicWindow);
    winMesh.position.set(doorW / 2, 0, 0.01);
    leftHinge.add(winMesh);

    // Chrome Door Latch Handle
    const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.28, 12), this.materials.doorHandle);
    handle.position.set(doorW - 0.06, 0, 0.04);
    leftHinge.add(handle);

    this.cabinetGroup.add(leftHinge);

    // Right Door (Hinged open at ~80 degrees)
    const rightHinge = new THREE.Group();
    rightHinge.position.set(cw / 2, 0, cd / 2);
    rightHinge.rotation.y = 1.4;

    const rightDoorFrame = new THREE.Mesh(
      new THREE.BoxGeometry(doorW, ch - 0.08, 0.03),
      this.materials.enclosureDoor
    );
    rightDoorFrame.position.set(-doorW / 2, 0, 0);
    rightHinge.add(rightDoorFrame);

    this.cabinetGroup.add(rightHinge);
  }

  buildCIOCControllers() {
    const ciocGroup = new THREE.Group();
    ciocGroup.position.set(0, 1.35, -0.32);

    const controllers = [
      { id: 'CIOC-01', label: 'PRIMARY CIOC-01', x: -0.28, active: true },
      { id: 'CIOC-02', label: 'STANDBY CIOC-02', x: 0.28, active: false }
    ];

    controllers.forEach(ctrl => {
      const cBox = new THREE.Mesh(
        new THREE.BoxGeometry(0.44, 0.48, 0.22),
        this.materials.controllerChassis
      );
      cBox.position.set(ctrl.x, 0, 0);
      cBox.castShadow = true;
      ciocGroup.add(cBox);

      // Status Bezel & LED
      const bezel = new THREE.Mesh(
        new THREE.BoxGeometry(0.38, 0.1, 0.02),
        new THREE.MeshStandardMaterial({ color: 0x131817 })
      );
      bezel.position.set(ctrl.x, 0.16, 0.12);
      ciocGroup.add(bezel);

      // Controller LED
      const led = new THREE.Mesh(
        new THREE.SphereGeometry(0.012, 16, 16),
        ctrl.active ? this.materials.ledGreen : this.materials.ledAmber
      );
      led.position.set(ctrl.x + 0.12, 0.16, 0.135);
      ciocGroup.add(led);

      // Ethernet Ports
      for (let p = 0; p < 2; p++) {
        const port = new THREE.Mesh(
          new THREE.BoxGeometry(0.04, 0.035, 0.02),
          new THREE.MeshStandardMaterial({ color: 0x090c0b, metalness: 0.5 })
        );
        port.position.set(ctrl.x - 0.1 + p * 0.06, -0.12, 0.115);
        ciocGroup.add(port);
      }
    });

    this.cabinetGroup.add(ciocGroup);
  }

  buildCableDucts() {
    const ductMat = this.materials.wireDuct;

    // Vertical side & center ducts
    [-0.82, 0, 0.82].forEach(x => {
      const vDuct = new THREE.Mesh(new THREE.BoxGeometry(0.12, 3.2, 0.14), ductMat);
      vDuct.position.set(x, 0, -0.34);
      this.cabinetGroup.add(vDuct);
    });

    // Horizontal cross ducts
    [1.05, -0.12, -1.25].forEach(y => {
      const hDuct = new THREE.Mesh(new THREE.BoxGeometry(1.64, 0.1, 0.14), ductMat);
      hDuct.position.set(0, y, -0.34);
      this.cabinetGroup.add(hDuct);
    });
  }

  buildCableGlands() {
    // Bottom Gland Entry Plate
    const glandPlate = new THREE.Mesh(
      new THREE.BoxGeometry(1.5, 0.02, 0.35),
      this.materials.galvanizedSteel
    );
    glandPlate.position.set(0, -1.72, -0.3);
    this.cabinetGroup.add(glandPlate);

    // Cable entry glands (represented as small brass hex cylinders)
    const glandMat = new THREE.MeshStandardMaterial({ color: 0xbcaaa4, metalness: 0.8, roughness: 0.3 });
    [-0.55, -0.35, -0.15, 0.15, 0.35, 0.55].forEach(gx => {
      const gland = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.04, 8), glandMat);
      gland.position.set(gx, -1.70, -0.3);
      this.cabinetGroup.add(gland);
    });
  }

  /**
   * Builds the 4 baseplates with high-contrast text plaques, 64 slots, and terminal blocks.
   */
  buildBaseplates() {
    const bpConfigs = [
      { id: 'BP-01', name: 'AI 4-20mA HART', rail: 1, x: -0.42, y: 0.42, isIS: false, color: '#e0e0e0', tagBg: '#1f2423' },
      { id: 'BP-02', name: 'HART / IS Barrier [Ex-ia]', rail: 1, x: 0.42, y: 0.42, isIS: true, color: '#90caf9', tagBg: '#0d47a1' },
      { id: 'BP-03', name: 'RTD / TC Temperature [mV]', rail: 2, x: -0.42, y: -0.65, isIS: false, color: '#ffe082', tagBg: '#bf360c' },
      { id: 'BP-04', name: 'DI / DO 24VDC Discrete', rail: 2, x: 0.42, y: -0.65, isIS: false, color: '#80cbc4', tagBg: '#004d40' }
    ];

    bpConfigs.forEach(bp => {
      const bpGroup = new THREE.Group();
      bpGroup.position.set(bp.x, bp.y, -0.35);

      // Baseplate carrier back
      const carrierGeo = new THREE.BoxGeometry(0.68, 0.92, 0.05);
      const carrier = new THREE.Mesh(carrierGeo, this.materials.charmCarrier);
      carrier.castShadow = true;
      bpGroup.add(carrier);

      // High-Contrast Baseplate Title Plaque
      const plaqueMesh = this.createTextPlaque(`${bp.id}: ${bp.name}`, bp.color, bp.tagBg, 512, 64);
      plaqueMesh.position.set(0, 0.43, 0.035);
      bpGroup.add(plaqueMesh);

      // 16 CHARM slots arranged in 2 columns of 8
      for (let i = 1; i <= 16; i++) {
        const slotKey = `${bp.id}-CH-${String(i).padStart(2, '0')}`;
        const col = i <= 8 ? 0 : 1;
        const row = (i - 1) % 8;

        const posX = (col === 0 ? -0.16 : 0.16);
        const posY = 0.33 - row * 0.095;
        const posZ = 0.04;

        // Slot module container
        const slotGroup = new THREE.Group();
        slotGroup.position.set(posX, posY, posZ);

        // Terminal Block Base
        const tbMesh = new THREE.Mesh(
          new THREE.BoxGeometry(0.26, 0.078, 0.04),
          this.materials.terminalBlock
        );
        slotGroup.add(tbMesh);

        // Channel Number Label Badge (e.g. "1", "2")
        const chLabel = this.createTextPlaque(`${i}`, '#ffffff', '#263238', 64, 64);
        chLabel.scale.set(0.04, 0.04, 1);
        chLabel.position.set(col === 0 ? -0.11 : 0.11, 0.02, 0.025);
        slotGroup.add(chLabel);

        // Two terminal screw heads
        [-0.06, 0.06].forEach(sx => {
          const screw = new THREE.Mesh(
            new THREE.CylinderGeometry(0.009, 0.009, 0.015, 12),
            this.materials.screwHead
          );
          screw.rotation.x = Math.PI / 2;
          screw.position.set(sx, 0.02, 0.022);
          slotGroup.add(screw);
        });

        // CHARM Module Cap (Selectable Target)
        let initialCapMat = this.materials.capAllocated;
        if (i >= 15) initialCapMat = this.materials.capSpare;
        if (bp.id === 'BP-02') initialCapMat = (i >= 15 ? this.materials.capSpare : this.materials.capISBlue);

        const capMesh = new THREE.Mesh(
          new THREE.BoxGeometry(0.12, 0.052, 0.035),
          initialCapMat
        );
        capMesh.position.set(0, -0.01, 0.03);
        capMesh.castShadow = true;
        // Attach metadata for raycasting
        capMesh.userData = {
          slotId: slotKey,
          baseplateId: bp.id,
          slotNumber: i,
          isIS: bp.isIS
        };
        slotGroup.add(capMesh);

        // Status LED diode
        const ledMesh = new THREE.Mesh(
          new THREE.SphereGeometry(0.007, 12, 12),
          i >= 15 ? this.materials.ledOff : this.materials.ledGreen
        );
        ledMesh.position.set(0.04, -0.01, 0.05);
        slotGroup.add(ledMesh);

        bpGroup.add(slotGroup);

        // Register in slot registry
        this.slots.set(slotKey, {
          slotId: slotKey,
          baseplateId: bp.id,
          slotNumber: i,
          mesh: capMesh,
          led: ledMesh,
          group: slotGroup,
          status: (i >= 15 ? 'SPARE' : 'ALLOCATED'),
          isIS: bp.isIS,
          signalTag: `TAG-${bp.id}-${String(i).padStart(2, '0')}`,
          defaultMaterial: initialCapMat,
          worldPos: new THREE.Vector3()
        });
      }

      this.cabinetGroup.add(bpGroup);
    });
  }

  /**
   * Creates a crisp text plaque mesh using HTML Canvas texture for readable 3D labels.
   */
  createTextPlaque(text, textColor, bgColor, width = 256, height = 64) {
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');

    // Background
    ctx.fillStyle = bgColor;
    ctx.fillRect(0, 0, width, height);

    // Border
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 3;
    ctx.strokeRect(1, 1, width - 2, height - 2);

    // Text
    ctx.fillStyle = textColor;
    ctx.font = 'bold 24px monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, width / 2, height / 2);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    const mat = new THREE.MeshBasicMaterial({ map: texture, transparent: false });
    const geo = new THREE.PlaneGeometry(0.64, 0.08);
    return new THREE.Mesh(geo, mat);
  }

  setupTooltip() {
    this.tooltip = document.createElement('div');
    this.tooltip.id = 'cad-3d-tooltip';
    this.tooltip.className = 'fixed z-50 pointer-events-none bg-neutral-900/95 text-neutral-100 text-xs font-mono p-2.5 rounded border border-neutral-700 shadow-xl opacity-0 transition-opacity duration-150';
    this.tooltip.style.transform = 'translate(-50%, -125%)';
    document.body.appendChild(this.tooltip);
  }

  setupInteractions() {
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2();
    this.isDragging = false;
    this.previousMousePosition = { x: 0, y: 0 };

    const dom = this.renderer.domElement;

    dom.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      this.previousMousePosition = { x: e.clientX, y: e.clientY };
    });

    dom.addEventListener('mousemove', (e) => {
      const rect = dom.getBoundingClientRect();
      this.mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      this.mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (this.isDragging) {
        const deltaX = e.clientX - this.previousMousePosition.x;
        const deltaY = e.clientY - this.previousMousePosition.y;

        if (e.buttons === 1) { // Left click: Orbit
          this.targetSpherical.theta -= deltaX * 0.006;
          this.targetSpherical.phi = Math.max(0.2, Math.min(Math.PI - 0.2, this.targetSpherical.phi - deltaY * 0.006));
        } else if (e.buttons === 2) { // Right click: Pan
          this.targetLookAt.x -= deltaX * 0.003;
          this.targetLookAt.y += deltaY * 0.003;
        }

        this.previousMousePosition = { x: e.clientX, y: e.clientY };
        this.hideTooltip();
      } else {
        this.handleHover(e);
      }
    });

    dom.addEventListener('mouseup', () => {
      this.isDragging = false;
    });

    dom.addEventListener('mouseleave', () => {
      this.isDragging = false;
      this.hideTooltip();
    });

    dom.addEventListener('contextmenu', (e) => e.preventDefault());

    dom.addEventListener('wheel', (e) => {
      e.preventDefault();
      this.targetSpherical.radius = Math.max(1.8, Math.min(9.5, this.targetSpherical.radius + e.deltaY * 0.004));
    }, { passive: false });

    dom.addEventListener('click', (e) => {
      this.handleClick(e);
    });
  }

  handleHover(e) {
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const clickables = Array.from(this.slots.values()).map(s => s.mesh);
    const intersects = this.raycaster.intersectObjects(clickables);

    if (intersects.length > 0) {
      const hit = intersects[0].object;
      const slotId = hit.userData.slotId;
      const slot = this.slots.get(slotId);
      this.container.style.cursor = 'pointer';

      if (slot) {
        this.showTooltip(e.clientX, e.clientY, slot);
      }
    } else {
      this.container.style.cursor = 'default';
      this.hideTooltip();
    }
  }

  showTooltip(x, y, slot) {
    if (!this.tooltip) return;
    const isIS = slot.isIS;
    const isAllocated = (slot.status === 'ALLOCATED');
    const statusIcon = isAllocated ? '✓ ALLOCATED' : (slot.status === 'CONFLICT' ? '⚠️ CONFLICT' : '⚪ SPARE');

    this.tooltip.innerHTML = `
      <div class="font-bold text-white text-[11px] flex items-center justify-between gap-3 border-b border-neutral-700 pb-1 mb-1">
        <span>${slot.slotId}</span>
        <span class="text-[10px] px-1 py-0.2 rounded ${isIS ? 'bg-blue-900 text-blue-200' : 'bg-neutral-800 text-neutral-300'}">
          ${isIS ? 'Ex-ia IS BARRIER' : 'STANDARD'}
        </span>
      </div>
      <div class="text-[10px] text-neutral-300">Signal: <strong class="text-white">${slot.signalTag || 'None (Unallocated)'}</strong></div>
      <div class="text-[10px] text-neutral-400">Status: <span class="${isAllocated ? 'text-green-400 font-semibold' : (slot.status === 'CONFLICT' ? 'text-red-400 font-semibold' : 'text-neutral-400')}">${statusIcon}</span></div>
      <div class="text-[9px] text-neutral-500 mt-0.5">Click to highlight & trace wire schedule</div>
    `;
    this.tooltip.style.left = `${x}px`;
    this.tooltip.style.top = `${y}px`;
    this.tooltip.style.opacity = '1';
  }

  hideTooltip() {
    if (this.tooltip) {
      this.tooltip.style.opacity = '0';
    }
  }

  handleClick(e) {
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const clickables = Array.from(this.slots.values()).map(s => s.mesh);
    const intersects = this.raycaster.intersectObjects(clickables);

    if (intersects.length > 0) {
      const hit = intersects[0].object;
      const slotId = hit.userData.slotId;
      if (slotId) {
        this.selectSlot(slotId, true);
      }
    }
  }

  /**
   * Highlights a slot in 3D, draws connection wire spline, and updates HUD.
   */
  selectSlot(slotId, triggerCallback = false) {
    // Restore previous selection appearance
    if (this.selectedSlotId && this.slots.has(this.selectedSlotId)) {
      const prev = this.slots.get(this.selectedSlotId);
      prev.mesh.material = prev.defaultMaterial;
    }

    this.selectedSlotId = slotId;

    if (slotId && this.slots.has(slotId)) {
      const slot = this.slots.get(slotId);
      slot.mesh.material = this.materials.capSelected;

      // Draw connection cable routing spline
      this.drawWireConnection(slot);

      // Smooth camera pan toward slot
      const worldPos = new THREE.Vector3();
      slot.group.getWorldPosition(worldPos);
      this.targetLookAt.copy(worldPos);
      this.targetSpherical.radius = Math.max(2.5, Math.min(3.8, this.targetSpherical.radius));

      if (triggerCallback) {
        this.onSelectCallback(slotId, slot);
      }
    } else {
      this.clearWireConnection();
    }
  }

  /**
   * Draws a visible 3D CatmullRom spline wire routing from the bottom gland plate,
   * up the side Panduit duct, and terminating directly on the terminal screws.
   */
  drawWireConnection(slot) {
    this.clearWireConnection();

    const worldPos = new THREE.Vector3();
    slot.group.getWorldPosition(worldPos);

    // Build CatmullRom path points
    const ductX = slot.baseplateId.endsWith('01') || slot.baseplateId.endsWith('03') ? -0.82 : 0.82;
    const glandY = -1.70;
    const glandZ = -0.30;

    const points = [
      new THREE.Vector3(ductX * 0.7, glandY, glandZ),
      new THREE.Vector3(ductX, -1.2, -0.34),
      new THREE.Vector3(ductX, worldPos.y, -0.34),
      new THREE.Vector3(worldPos.x + (ductX > 0 ? 0.08 : -0.08), worldPos.y, -0.32),
      new THREE.Vector3(worldPos.x, worldPos.y + 0.02, worldPos.z + 0.02)
    ];

    const curve = new THREE.CatmullRomCurve3(points);
    const tubeGeo = new THREE.TubeGeometry(curve, 32, 0.008, 8, false);
    this.wireMesh = new THREE.Mesh(tubeGeo, this.materials.wireActive);
    this.scene.add(this.wireMesh);
  }

  clearWireConnection() {
    if (this.wireMesh) {
      this.scene.remove(this.wireMesh);
      if (this.wireMesh.geometry) this.wireMesh.geometry.dispose();
      this.wireMesh = null;
    }
  }

  updateHardwareState(hardwarePositions, assignments = {}, signalsList = []) {
    const posMap = new Map();
    hardwarePositions.forEach(p => posMap.set(p.id, p));

    const sigMap = new Map();
    if (signalsList) {
      signalsList.forEach(s => {
        if (s.assigned_position_id) {
          sigMap.set(s.assigned_position_id, s);
        }
      });
    }

    this.slots.forEach((slot, slotId) => {
      const hw = posMap.get(slotId);
      if (!hw) return;

      slot.status = hw.status;
      slot.assignedSignalId = hw.assigned_signal_id;

      const sigObj = sigMap.get(slotId);
      if (sigObj) {
        slot.signalTag = sigObj.tag;
      } else if (hw.assigned_signal_id) {
        slot.signalTag = hw.assigned_signal_id;
      } else {
        slot.signalTag = null;
      }

      let mat = this.materials.capSpare;
      let ledMat = this.materials.ledOff;

      if (hw.status === 'ALLOCATED') {
        mat = hw.is_is_rated ? this.materials.capISBlue : this.materials.capAllocated;
        ledMat = this.materials.ledGreen;
      } else if (hw.status === 'WARNING') {
        mat = this.materials.capWarning;
        ledMat = this.materials.ledAmber;
      } else if (hw.status === 'CONFLICT') {
        mat = this.materials.capConflict;
        ledMat = this.materials.ledRed;
      } else if (hw.status === 'RESERVED') {
        mat = this.materials.capSpare;
        ledMat = this.materials.ledOff;
      }

      slot.defaultMaterial = mat;
      if (this.selectedSlotId === slotId) {
        slot.mesh.material = this.materials.capSelected;
      } else {
        slot.mesh.material = mat;
      }
      slot.led.material = ledMat;
    });

    this.applyStatusFilter(this.activeFilter);
  }

  applyStatusFilter(filterType) {
    this.activeFilter = filterType;
    this.slots.forEach(slot => {
      if (filterType === 'ALL') {
        slot.group.visible = true;
      } else if (filterType === 'ALLOCATED') {
        slot.group.visible = (slot.status === 'ALLOCATED');
      } else if (filterType === 'AVAILABLE') {
        slot.group.visible = (slot.status === 'AVAILABLE' || slot.status === 'RESERVED' || slot.status === 'SPARE');
      } else if (filterType === 'WARNING') {
        slot.group.visible = (slot.status === 'WARNING');
      } else if (filterType === 'CONFLICT') {
        slot.group.visible = (slot.status === 'CONFLICT');
      }
    });
  }

  setCameraPreset(preset) {
    if (preset === 'ISO' || preset === 'RESET') {
      this.targetSpherical = { radius: 6.4, theta: 0.42, phi: 1.25 };
      this.targetLookAt = this.initialLookAt.clone();
    } else if (preset === 'FRONT' || preset === 'FIT') {
      this.targetSpherical = { radius: 5.6, theta: 0.0, phi: Math.PI / 2 };
      this.targetLookAt = new THREE.Vector3(0, 0, 0);
    } else if (preset === 'CIOC') {
      this.targetSpherical = { radius: 2.8, theta: 0.1, phi: 1.4 };
      this.targetLookAt = new THREE.Vector3(0, 1.35, -0.2);
    } else if (preset === 'BP-01') {
      this.targetSpherical = { radius: 2.4, theta: 0.12, phi: 1.5 };
      this.targetLookAt = new THREE.Vector3(-0.42, 0.42, -0.3);
    } else if (preset === 'BP-02') {
      this.targetSpherical = { radius: 2.4, theta: -0.12, phi: 1.5 };
      this.targetLookAt = new THREE.Vector3(0.42, 0.42, -0.3);
    } else if (preset === 'BP-03') {
      this.targetSpherical = { radius: 2.4, theta: 0.12, phi: 1.5 };
      this.targetLookAt = new THREE.Vector3(-0.42, -0.65, -0.3);
    } else if (preset === 'BP-04') {
      this.targetSpherical = { radius: 2.4, theta: -0.12, phi: 1.5 };
      this.targetLookAt = new THREE.Vector3(0.42, -0.65, -0.3);
    }
  }

  updateCameraPosition() {
    const s = this.spherical;
    const x = s.radius * Math.sin(s.phi) * Math.sin(s.theta);
    const y = s.radius * Math.cos(s.phi);
    const z = s.radius * Math.sin(s.phi) * Math.cos(s.theta);

    this.camera.position.set(x + this.cameraLookAt.x, y + this.cameraLookAt.y, z + this.cameraLookAt.z);
    this.camera.lookAt(this.cameraLookAt);
  }

  animate() {
    requestAnimationFrame(() => this.animate());

    // Smooth camera interpolation
    const lerpFactor = 0.085;
    this.spherical.radius += (this.targetSpherical.radius - this.spherical.radius) * lerpFactor;
    this.spherical.theta += (this.targetSpherical.theta - this.spherical.theta) * lerpFactor;
    this.spherical.phi += (this.targetSpherical.phi - this.spherical.phi) * lerpFactor;

    this.cameraLookAt.lerp(this.targetLookAt, lerpFactor);
    this.updateCameraPosition();

    if (this.renderer && this.scene && this.camera) {
      this.renderer.render(this.scene, this.camera);
    }
  }

  onResize() {
    if (!this.container || !this.renderer) return;
    this.width = this.container.clientWidth;
    this.height = this.container.clientHeight;
    this.camera.aspect = this.width / this.height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(this.width, this.height);
  }
}

window.Cabinet3DViewer = Cabinet3DViewer;
