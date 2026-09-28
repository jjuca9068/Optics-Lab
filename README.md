# Engineering & Physics Portfolio

Welcome to my project portfolio! This repository showcases custom CAD hardware, optical setups, and technical engineering projects developed for research and practical application.

## 📋 Table of Contents
1. [Quantum Optics Lab Stage Mounts](#1-quantum-optics-lab-stage-mounts)
2. [Project 2: [Insert Title]](#2-project-2-insert-title)
3. [Project 3: [Insert Title]](#3-project-3-insert-title)

---

# 1. Quantum Optics Lab Stage Mounts
Personal portfolio and technical projects for the MTSU Quantum Optics Lab, featuring custom CAD hardware, mechanical frame layouts, and an AI-assisted instrument control system.

### 1.1 Project Task & Engineering Challenge
* **Objective:** Securely mount specialized fiber holders onto translational stages to draw optical fiber under controlled tension over a hydrogen flame.
* **Constraints:** Commercial stage hardware lacked the proper clearance, vertical offset, and stability required for precise repeatable results.
* **Goal:** Design, iterate, and deploy a custom, high-rigidity stage mount to optimize precision and repeatability.

---

### 1.2 Design Logic & Prototyping Approach
* **Modular Two-Part System:** Split the mount into a **Base Plate** (interfaces directly with the stage) and a **Top Bracket** (clamps the fiber fixture) for fast alignment adjustments and component swapping.
* **Universal Dual-Hole Pattern:** Integrated symmetric mounting holes into the base plate design. This allows a single printed part to be deployed interchangeably on either the left or right side of the stage setup, eliminating the need to design and manage separate left- and right-handed models.
* **Prototyping Strategy:** Utilized 3D-printed PETG/PLA for rapid dimensional validation and clearance testing before final deployment.
* **Thermal Considerations:** Designed clearance offsets relative to the flame source to prevent localized heating or material sagging during active fiber drawing runs.

---

### 1.3 Iteration History & Development

#### Phase 1: Early Prototypes & Initial Fit Check
Initial spatial checks to test stage mounting hole spacing and overall base plate geometry.

| Base Plate (V1) | Stage Fit Check Assembly |
| :---: | :---: |
| ![Base V1](Base-V1.jpeg) | ![Test Assembly](Test-Base-V1.jpeg) |
| *Initial base mounting plate* | *Assembled fit-check on stage* |

---

#### Phase 2: Top Bracket & Binding Clearance Analysis
Evaluating upper bracket geometry and identifying translation binding issues.

| Top Bracket (V1) | Failed Fit Check (Side View) |
| :---: | :---: |
| ![Top V1](Top-V1.jpeg) | ![Failed Side View](Base-Top-Failed-SideView.jpeg) |
| *First top bracket geometry* | *Side view clearance breakdown* |

* **Key Finding:** Initial V1 geometry created binding along the translation vector. Adjustments were made to side offsets and hole counterbores for subsequent revisions.

---

#### Phase 3: Refined Base Plate Geometry & Alignment Fit
Upgraded base plate design featuring reinforced side walls, corrected stage hole tolerances, and physical fit verification.

| Base Plate (V2) | Alignment Verification |
| :---: | :---: |
| ![Base V2](Base-V2.jpeg) | ![Failed Alignment](Base-Top-Failed.jpeg) |
| *Reinforced base plate V2* | *Alignment verification and clearance test* |

---

#### Phase 4: Final Production Setup
Final assembly integrated and active in the laboratory fiber tapering rig.

| Final Deployment | Overhead View | Mount Interface Detail |
| :---: | :---: | :---: |
| ![Final Assembly](Final-Product-In-Action.jpeg) | ![Top View](Final-Product-In-Action-Top-View.jpeg) | ![Untopped](Final-Product-In-Action-Untopped.jpeg) |
| *In operation over hydrogen flame* | *Overhead optical alignment check* | *Stage mounting interface* |

---

### 1.4 3D Printable Models (STL)

Click any link below to view or rotate the 3D models directly on GitHub:

* **[Final Design](Final_Design.stl)**
* **[Full Base V2](Full_Base_V2.stl)**
* **[Top V2](Top_V2.stl)**
* **[Top V1](Top_V1.stl)**
* **[Full Base V1](Full_Base_V1.stl)**
* **[Base V1](Base_v1.stl)**
* **[Prototype 2](Prototype_number_2.stl)**
* **[Prototype 1](Prototype_number_1.stl)**

---

### 1.5 Summary & Key Results
* **Alignment & Versatility:** Successfully eliminated stage binding with a dual-hole universal base plate that mounts on either side of the setup.
* **Rigidity:** Modular clamp system holds fiber under tension without mechanical drift.
* **Cost & Time:** Iterated through spatial fit checks via 3D printing in hours, bypassing expensive trial-and-error machining.

---

# 2. Project 2: [Insert Title]
*(Description and overview coming soon...)*

---

# 3. Project 3: [Insert Title]
*(Description and overview coming soon...)*
