# Optics-Lab
Personal portfolio and technical projects for the MTSU Quantum Optics Lab, featuring custom CAD hardware, mechanical frame layouts, and an AI assisted instrument control system.

## 1. Project Task & Engineering Challenge
* **Objective:** Securely mount specialized fiber holders onto translational stages to draw optical fiber under controlled tension over a hydrogen flame.
* **Constraints:** Commercial stage hardware lacked the proper clearance, vertical offset, and stability required for precise repeatable results.
* **Goal:** Design, iterate, and deploy a custom, high-rigidity stage mount to optimize precision and repeatability.

---

## 2. Design Logic & Prototyping Approach
* **Modular Two-Part System:** Split the mount into a **Base Plate** (interfaces directly with the stage) and a **Top Bracket** (clamps the fiber fixture) for fast alignment adjustments and component swapping.
* **Universal Dual-Hole Pattern:** Integrated symmetric mounting holes into the base plate design. This allows a single printed part to be deployed interchangeably on either the left or right side of the stage setup, eliminating the need to design and manage separate left- and right-handed models.
* **Prototyping Strategy:** Utilized 3D-printed PETG/PLA for rapid dimensional validation and clearance testing before final deployment.
* **Thermal Considerations:** Designed clearance offsets relative to the flame source to prevent localized heating or material sagging during active fiber drawing runs.

---

## 3. Iteration History & Development

### Phase 1: Early Prototypes & Initial Fit Check
Initial spatial checks to test stage mounting hole spacing and overall base plate geometry.

| Base Plate (V1) | Stage Fit Check Assembly |
| :---: | :---: |
| ![Base V1](Base-V1.jpeg) | ![Test Assembly](Test-Base-V1.jpeg) |
| *Initial base mounting plate* | *Assembled fit-check on stage* |

---

### Phase 2: Top Bracket & Binding Clearance Analysis
Evaluating upper bracket geometry and identifying translation binding issues.

| Top Bracket (V1) | Failed Fit Check (Side View) |
| :---: | :---: |
| ![Top V1](Top-V1.jpeg) | ![Failed Side View](Base-Top-Failed-SideView.jpeg) |
| *First top bracket geometry* | *Side view clearance breakdown* |

* **Key Finding:** Initial V1 geometry created binding along the translation vector. Adjustments were made to side offsets and hole counterbores for subsequent revisions.

---

### Phase 3: Refined Base Plate Geometry
Upgraded base plate design featuring reinforced side walls and corrected stage hole tolerances.

| Base Plate (V2) |
| :---: |
| ![Base V2](Base-V2.jpeg) |
| *Reinforced base plate V2* |

---

### Phase 4: Final Production Setup
Final assembly integrated and active in the laboratory fiber tapering rig.

| Final Deployment | Overhead View | Mount Interface Detail |
| :---: | :---: | :---: |
| ![Final Assembly](Final-Product-In-Action.jpeg) | ![Top View](Final-Product-In-Action-Top-View.jpeg) | ![Untopped](Final-Product-In-Action-Untopped.jpeg) |
| *In operation over hydrogen flame* | *Overhead optical alignment check* | *Stage mounting interface* |

---

## 4. 3D Printable Models (STL)

Click any link below to view or rotate the 3D models directly on GitHub:

* **[Base Plate Model](YOUR_BASE_PLATE_FILE.stl)**
* **[Top Bracket Model](YOUR_TOP_BRACKET_FILE.stl)**

---

## 5. Summary & Key Results
* **Alignment & Versatility:** Successfully eliminated stage binding with a dual-hole universal base plate that mounts on either side of the setup.
* **Rigidity:** Modular clamp system holds fiber under tension without mechanical drift.
* **Cost & Time:** Iterated through spatial fit checks via 3D printing in hours, bypassing expensive trial-and-error machining.
