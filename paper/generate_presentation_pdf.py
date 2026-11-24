#!/usr/bin/env python3
"""
generate_presentation_pdf.py
Builds the comprehensive 17-slide capstone review presentation: preparation.pdf.
Features:
- High-resolution 16:9 widescreen layout (13.33 x 7.5 inches at 150 DPI)
- Embedded real annotated sample photo from model_specification/images
- Comprehensive visual diagrams for the 4-stage pipeline, body markings, and pinhole geometry
- Detailed mathematical and statistical definitions (MAE, RMSE, Bias, R^2, Median baseline, Calibration)
- Full walkthrough of all empirical tables (Tables I through IX) and graphs (Figs 3 & 4)
- Operational boundaries, failure modes, error causes, and viva defense cheat-sheet
- Clean typography, strictly bounded cards, zero text collisions or overlapping
"""

import os
import sys

# Ensure clean cache directory
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib_capstone"
os.makedirs("/tmp/matplotlib_capstone", exist_ok=True)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
from PIL import Image

OUTPUT_PDF = "/Users/chintalapudithanooz/Documents/Projects/capstone/preparation.pdf"
SAMPLE_IMG_PATH = "/Users/chintalapudithanooz/Documents/Projects/capstone/paper/presentation_assets/sample_annotated.jpg"

# Color Palette
NAVY_DARK = "#0F172A"
NAVY_HEADER = "#1E293B"
BG_LIGHT = "#F8FAFC"
WHITE = "#FFFFFF"
TEAL = "#0D9488"
BLUE_ACCENT = "#2563EB"
CYAN_ACCENT = "#0284C7"
AMBER_WARN = "#D97706"
GREEN_PASS = "#16A34A"
RED_ERR = "#DC2626"
GRAY_TEXT = "#1E293B"
GRAY_BODY = "#334155"
GRAY_MUTED = "#64748B"
BORDER_COLOR = "#CBD5E1"

def create_slide_base(title, category="CAPSTONE VIVA PREPARATION DECK", slide_num=1, total_slides=17):
    fig = plt.figure(figsize=(13.33, 7.5), dpi=150)
    fig.patch.set_facecolor(BG_LIGHT)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 13.33)
    ax.set_ylim(0, 7.5)
    ax.axis("off")
    
    # Top Header Banner
    header = patches.Rectangle((0, 6.45), 13.33, 1.05, facecolor=NAVY_HEADER, edgecolor="none", zorder=1)
    ax.add_patch(header)
    
    # Accent stripe under banner
    stripe = patches.Rectangle((0, 6.38), 13.33, 0.07, facecolor=TEAL, edgecolor="none", zorder=2)
    ax.add_patch(stripe)
    
    # Category tag
    ax.text(0.60, 7.15, category.upper(), fontsize=9, fontweight="bold", color=TEAL, va="center", zorder=3)
    # Title
    ax.text(0.60, 6.75, title, fontsize=18, fontweight="bold", color=WHITE, va="center", zorder=3)
    
    # Slide Number Tag
    ax.text(12.73, 6.75, f"Slide {slide_num} of {total_slides}", fontsize=10, fontweight="bold", color="#94A3B8", ha="right", va="center", zorder=3)
    
    # Footer Banner
    footer = patches.Rectangle((0, 0), 13.33, 0.38, facecolor="#E2E8F0", edgecolor="none", zorder=1)
    ax.add_patch(footer)
    ax.text(0.60, 0.19, "Human Height & Weight Estimation from RGB Images | Department of Computer Science & Engineering", 
            fontsize=8, color=GRAY_MUTED, va="center")
    ax.text(12.73, 0.19, "Final Viva & Review Preparation", fontsize=8, fontweight="bold", color=NAVY_HEADER, ha="right", va="center")
    
    return fig, ax

def draw_card(ax, x, y, w, h, bg=WHITE, border=BORDER_COLOR, lw=1.2, radius=0.08):
    box = patches.FancyBboxPatch((x, y), w, h, boxstyle=f"round,pad=0.02,rounding_size={radius}", 
                                 facecolor=bg, edgecolor=border, linewidth=lw, zorder=2)
    ax.add_patch(box)
    return box

def draw_badge(ax, x, y, text, bg=TEAL, fg=WHITE, fontsize=8.5):
    ax.text(x, y, f"  {text}  ", fontsize=fontsize, fontweight="bold", color=fg,
            bbox=dict(boxstyle="round,pad=0.22,rounding_size=0.1", facecolor=bg, edgecolor="none"),
            va="center", ha="left", zorder=5)

# ==============================================================================
# SLIDE 1: COVER SLIDE
# ==============================================================================
def make_slide_1(pdf):
    fig = plt.figure(figsize=(13.33, 7.5), dpi=150)
    fig.patch.set_facecolor(NAVY_DARK)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 13.33)
    ax.set_ylim(0, 7.5)
    ax.axis("off")
    
    # Gradient accent block
    accent = patches.Rectangle((0, 7.35), 13.33, 0.15, facecolor=TEAL, edgecolor="none")
    ax.add_patch(accent)
    
    # Tag
    ax.text(1.00, 6.35, "CAPSTONE THESIS FINAL DEFENSE & COMPREHENSIVE VIVA GUIDE", fontsize=11, fontweight="bold", color=TEAL, va="center")
    
    # Main Title
    ax.text(1.00, 5.40, "A Camera-Geometry & Body-Proportion Approach for\nReal-Time Image-Based Height and Weight Estimation", 
            fontsize=23, fontweight="bold", color=WHITE, va="center", linespacing=1.25)
    
    # Subtitle
    ax.text(1.00, 4.35, "Coupling Deterministic Optical Physics with Deep Pose Keypoints and Regularized Machine Learning", 
            fontsize=12.5, color="#94A3B8", va="center")
    
    # Metadata Card
    card = patches.FancyBboxPatch((1.00, 1.15), 11.33, 2.75, boxstyle="round,pad=0.05,rounding_size=0.12",
                                  facecolor=NAVY_HEADER, edgecolor="#334155", linewidth=1.5)
    ax.add_patch(card)
    
    ax.text(1.40, 3.55, "PROJECT BENCHMARK HIGHLIGHTS & ARCHITECTURAL SUMMARY", fontsize=11, fontweight="bold", color=CYAN_ACCENT)
    
    facts = [
        ("Height Estimation:", "Calibrated Stature MAE 4.14 cm (88.7% error reduction over raw optical pinhole)"),
        ("Weight Estimation:", "Front-View MAE 7.00 kg | Fused Dual-View MAE 6.47 kg (R^2 = 0.618)"),
        ("Clinical Triage:", "78.8% Exact WHO BMI Bin Agreement | 97.4% Adjacent-Tier Agreement"),
        ("Execution Latency:", "62.0 ms End-to-End on Commodity CPU (~16.1 FPS Real-Time Feasibility)"),
        ("Validation Protocol:", "151 Images, 37 Participants under Strict 5-Fold GroupKFold (Zero Leakage)")
    ]
    
    for idx, (label, val) in enumerate(facts):
        y_pos = 3.10 - idx * 0.40
        ax.text(1.40, y_pos, f"-  {label}", fontsize=9.5, fontweight="bold", color="#CBD5E1")
        ax.text(3.50, y_pos, val, fontsize=9.5, color=WHITE)
        
    ax.text(1.00, 0.55, "Department of Computer Science & Engineering | Academic Year 2026", fontsize=9, color="#64748B")
    ax.text(12.33, 0.55, "Slide 1 of 17", fontsize=9, fontweight="bold", color="#64748B", ha="right")
    
    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 2: MOTIVATION & 3 VISION CHALLENGES
# ==============================================================================
def make_slide_2(pdf):
    fig, ax = create_slide_base("Project Motivation & The 3 Core Computer Vision Challenges", slide_num=2)
    
    # Left Card: Motivation
    draw_card(ax, 0.60, 0.60, 5.85, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "THE MOTIVATION", bg=BLUE_ACCENT)
    ax.text(0.90, 5.35, "Why Contactless Anthropometry?", fontsize=13.5, fontweight="bold", color=NAVY_DARK)
    
    m_sections = [
        ("Traditional Physical Measurements are Intrusive:", [
            "Requires stadiometers for stature and mechanical beam scales for mass.",
            "Completely impractical in remote telemedicine, rural triage, and decentralized clinics."
        ]),
        ("High Demand in Modern Digital Health & Virtual Workflows:", [
            "- Telemedicine & Pediatric Triage: Remote nutritional tracking and dosage calibration.",
            "- Automated E-Commerce Sizing: Drastically reducing sizing-related apparel returns.",
            "- Smart Ergonomics & Biomechanics: Contactless workplace posture monitoring."
        ]),
        ("The Core Engineering Goal of Our Capstone:", [
            "Construct a fully non-contact, real-time estimation platform using standard",
            "commodity smartphone cameras without specialized depth sensors or intrusive markers."
        ])
    ]
    
    y_curr = 4.85
    for title, bullets in m_sections:
        ax.text(0.90, y_curr, title, fontsize=10, fontweight="bold", color=NAVY_DARK)
        y_curr -= 0.26
        for b in bullets:
            ax.text(0.90, y_curr, b, fontsize=8.5, color=GRAY_BODY)
            y_curr -= 0.22
        y_curr -= 0.16

    # Right Card: The 3 Fundamental Vision Challenges
    draw_card(ax, 6.85, 0.60, 5.88, 5.60, bg=WHITE)
    draw_badge(ax, 7.15, 5.80, "THE BOTTLENECKS", bg=AMBER_WARN)
    ax.text(7.15, 5.35, "The 3 Fundamental Computer Vision Challenges", fontsize=13.5, fontweight="bold", color=NAVY_DARK)
    
    c_boxes = [
        ("1. Scale Ambiguity in 2D Perspective Projection",
         "A 2D photo has no metric scale. A 180 cm adult at 2 meters casts the EXACT",
         "same pixel span as a 90 cm child at 1 meter! Pinhole math alone requires",
         "known camera mounting height C and subject distance D."),
        ("2. Volumetric & Compositional Deficit",
         "Stature is 1D length, but Weight is 3D physical mass (M = integral rho dV).",
         "A 2D silhouette conceals anteroposterior torso depth, skeletal density,",
         "hydration levels, and muscle-to-fat distribution."),
        ("3. Edge Computational & Operational Limits",
         "Prior works fit complex 3D meshes (e.g. SMPL optimization) taking 5-10 s",
         "per frame on GPUs, or place checkerboard markers on the floor.",
         "Our requirement: Instant sub-100ms CPU execution with pure Python/OpenCV.")
    ]
    
    y_card = 4.70
    for title, l1, l2, l3 in c_boxes:
        draw_card(ax, 7.10, y_card - 0.95, 5.38, 1.25, bg="#F1F5F9", border="#E2E8F0")
        ax.text(7.25, y_card + 0.08, title, fontsize=9.5, fontweight="bold", color=BLUE_ACCENT)
        ax.text(7.25, y_card - 0.20, l1, fontsize=8.2, color=GRAY_BODY)
        ax.text(7.25, y_card - 0.42, l2, fontsize=8.2, color=GRAY_BODY)
        ax.text(7.25, y_card - 0.64, l3, fontsize=8.2, color=GRAY_BODY)
        y_card -= 1.40

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 3: 4-STAGE ARCHITECTURAL PIPELINE
# ==============================================================================
def make_slide_3(pdf):
    fig, ax = create_slide_base("End-to-End Modular Architecture: The 4 Processing Stages", slide_num=3)
    
    stages = [
        ("STAGE 1: INGESTION & API", BLUE_ACCENT, [
            ("Client Interface", "React / Vite Web Portal (Drag & Drop)"),
            ("Input Parameters", "RGB Image(s), Distance D, Mount Height C"),
            ("FastAPI Service", "Async Multipart Router (/api/predict-body)"),
            ("Catalog Logging", "Continuous Record Storage (CSV Catalog)")
        ]),
        ("STAGE 2: COMPUTER VISION", TEAL, [
            ("YOLOv8 Nano", "Person Localization (Box b*, conf >= 0.40)"),
            ("MediaPipe Pose", "33 3D Keypoints + Posture Guard"),
            ("Posture Guard", "Knee angle check: theta_knee >= 160 deg"),
            ("Selfie Segmenter", "Silhouette Mask M + 3 Slices (x6, x7, x8)")
        ]),
        ("STAGE 3: GEOMETRY & ML", CYAN_ACCENT, [
            ("Pinhole Projection", "Ground-Contact Pitch Recovery -> Raw H_g"),
            ("Ridge Calibrator", "Compensates Lens Distortion (MAE 4.14 cm)"),
            ("Feature Extraction", "8 Scale-Invariant Ratios (x1 to x8)"),
            ("Ridge Regressor", "Scaled Body Mass Inference (MAE 7.28 kg)")
        ]),
        ("STAGE 4: FUSION & OUTPUT", NAVY_HEADER, [
            ("Multi-View Fusion", "Coronal-Sagittal Combination (6.47 kg MAE)"),
            ("OpenCV Engine", "Skeletal Rays & Metric Text Annotations"),
            ("Web Dashboard", "Interactive Metric Stature, Mass & BMI"),
            ("Clinical Triage", "WHO Category (UW, Normal, Over, Obese)")
        ])
    ]
    
    x_positions = [0.60, 3.69, 6.78, 9.87]
    card_w = 2.85
    
    for idx, (s_name, s_color, items) in enumerate(stages):
        x = x_positions[idx]
        draw_card(ax, x, 0.60, card_w, 5.60, bg=WHITE)
        
        # Header block of card
        h_box = patches.Rectangle((x, 5.60), card_w, 0.60, facecolor=s_color, edgecolor="none", zorder=3)
        ax.add_patch(h_box)
        ax.text(x + card_w/2, 5.90, s_name, fontsize=9.2, fontweight="bold", color=WHITE, ha="center", va="center", zorder=4)
        
        y_pos = 5.10
        for b_title, b_desc in items:
            draw_card(ax, x + 0.15, y_pos - 0.75, card_w - 0.30, 0.90, bg="#F8FAFC", border="#E2E8F0")
            ax.text(x + 0.25, y_pos - 0.15, b_title, fontsize=8.8, fontweight="bold", color=NAVY_DARK)
            ax.text(x + 0.25, y_pos - 0.42, b_desc, fontsize=7.6, color=GRAY_BODY)
            y_pos -= 1.10
            
        # Draw connector arrows between stages in the gap
        if idx < 3:
            ax.annotate("", xy=(x + card_w + 0.21, 3.40), xytext=(x + card_w + 0.03, 3.40),
                        arrowprops=dict(arrowstyle="->", color=TEAL, lw=2.5), zorder=5)

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 4: DATA JOURNEY - HOW THE IMAGE TRAVELS (2 COLUMNS)
# ==============================================================================
def make_slide_4(pdf):
    fig, ax = create_slide_base("Detailed Data Journey: How the Image Travels Step-by-Step", slide_num=4)
    
    col1_steps = [
        ("Step 1: Ingestion & Upload", 
         "User captures full-body picture via phone or web camera, enters standoff\ndistance D (e.g. 150 cm) and camera height C (100 cm). React client dispatches\nmultipart/form-data POST to the asynchronous FastAPI backend."),
        ("Step 2: In-Memory Stream Decode & Privacy", 
         "FastAPI server reads raw upload stream directly into RAM using OpenCV imdecode.\nNo unencrypted photo is written to persistent disk, preserving strict patient\nprivacy and compliance with healthcare data protection principles."),
        ("Step 3: YOLOv8 Person Detection", 
         "YOLOv8 Nano checks the frame at native resolution. Filters detections to retain\nhuman class (ID 0) with confidence >= 40%. Selects the largest bounding box b*\nto eliminate background pedestrians and extraneous clutter."),
        ("Step 4: MediaPipe Pose & Segmentation", 
         "A 15-pixel padded crop around b* is routed to MediaPipe Pose Lite (extracting\n33 3D skeletal keypoints) and Selfie Segmenter (generating a float16 binary\nforeground silhouette mask for cross-sectional geometric slicing).")
    ]
    
    col2_steps = [
        ("Step 5: Cranial & Ground Plane Anchoring", 
         "Head top y_top is anchored to the upper box edge; ground contact y_bottom is\ndetermined by the lowest heel/toe keypoint. Automated check confirms knee\nangle theta_knee >= 160 deg to reject slouching or bent-knee postures."),
        ("Step 6: Optical Projection & Ridge Calibration", 
         "Pinhole camera geometry calculates uncalibrated stature H_g using camera pitch.\nRidge calibrator adjusts for lens barrel distortion and foot joint offset,\nreducing stature error to 4.14 cm MAE (88.7% reduction)."),
        ("Step 7: 8 Anthropometric Slices & Weight Regression", 
         "Silhouettes are sliced across chest (30%), waist (52%), and hips (70%). Scaled\nRidge regressor predicts mass W. If dual-view is provided, coronal-sagittal convex\nfusion combines front and side predictions (6.47 kg MAE)."),
        ("Step 8: Visual Overlay & Continuous Catalog Logging", 
         "OpenCV paints bounding boxes, joints, and measurement labels. Returns base64\nimage + JSON metrics to dashboard. Prediction record is continuously logged\nin the persistent height_weight_dataset.csv catalog.")
    ]
    
    cols = [
        (0.60, 5.85, col1_steps, 1),
        (6.85, 5.88, col2_steps, 5)
    ]
    
    for cx, cw, steps, start_num in cols:
        y_card = 4.80
        for idx, (stitle, sdesc) in enumerate(steps):
            draw_card(ax, cx, y_card, cw, 1.22, bg=WHITE, border="#CBD5E1")
            
            # Step number circle
            step_num = start_num + idx
            circle = plt.Circle((cx + 0.35, y_card + 0.88), 0.20, color=BLUE_ACCENT if step_num % 2 == 1 else TEAL, zorder=3)
            ax.add_patch(circle)
            ax.text(cx + 0.35, y_card + 0.88, str(step_num), color=WHITE, fontsize=9, fontweight="bold", ha="center", va="center", zorder=4)
            
            ax.text(cx + 0.68, y_card + 0.88, stitle, fontsize=9.5, fontweight="bold", color=NAVY_DARK, va="center")
            
            # Multi-line description
            dy = 0.58
            for line in sdesc.split("\n"):
                ax.text(cx + 0.25, y_card + dy, line, fontsize=7.8, color=GRAY_BODY)
                dy -= 0.19
                
            # Connecting down arrow
            if idx < 3:
                ax.annotate("", xy=(cx + cw/2, y_card - 0.10), xytext=(cx + cw/2, y_card - 0.02),
                            arrowprops=dict(arrowstyle="->", color=TEAL, lw=1.8), zorder=5)
            y_card -= 1.35
            
    # Connector between columns (Step 4 to Step 5)
    ax.annotate("", xy=(6.80, 5.40), xytext=(6.50, 1.35),
                arrowprops=dict(arrowstyle="->", color=BLUE_ACCENT, lw=2.0, connectionstyle="arc3,rad=-0.25"), zorder=5)

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 5: HOW BODY MARKINGS ARE DONE
# ==============================================================================
def make_slide_5(pdf):
    fig, ax = create_slide_base("Anatomical Landmarks & Body Markings: How They Are Done", slide_num=5)
    
    # Left Card: Landmark Details
    draw_card(ax, 0.60, 0.60, 6.60, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "ANATOMICAL FORMULATION", bg=TEAL)
    ax.text(0.90, 5.35, "Extracting True Vertical Stature Boundaries", fontsize=13, fontweight="bold", color=NAVY_DARK)
    
    text_blocks = [
        ("The Pitfall of Facial Keypoints for Head Crown:", [
            "- Prior research extrapolates cranial top from eyes, nose, or ears.",
            "- When a subject tilts their chin up/down by 5 deg, or has voluminous hairstyles,",
            "  facial points drift by 5 to 15 cm, causing severe stature variance."
        ]),
        ("Solution 1: Cranial Apex (y_top) from Bounding Box:", [
            "- We anchor the cranial vertex directly to the top of the YOLOv8 person box: y_top = y1*",
            "- The horizontal coordinate is anchored at the shoulder midpoint: x_top = (x_sh,L + x_sh,R) / 2",
            "- Guarantees an anatomically stable, tilt-resistant crown apex!"
        ]),
        ("Solution 2: Bilateral Extremum Ground Contact (y_bottom):", [
            "- We evaluate all 4 candidate foot keypoints: Left/Right Heel and Left/Right Toe:",
            "    y_bottom = max(y_heel,L, y_heel,R, y_toe,L, y_toe,R)",
            "- Apparent Vertical Pixel Stature: p_h = |y_bottom - y_top|"
        ]),
        ("Solution 3: Automated Knee-Flexion Posture Guard:", [
            "- Vector dot product checks interior knee angle across hip, knee, and ankle.",
            "- If theta_knee < 160 deg on either leg, system flags an immediate posture warning,",
            "  preventing bent-knee or slouched standing from corrupting stature."
        ])
    ]
    
    y_pos = 4.90
    for title, lines in text_blocks:
        ax.text(0.90, y_pos, title, fontsize=9.0, fontweight="bold", color=NAVY_DARK)
        y_pos -= 0.20
        for l in lines:
            fw = "bold" if "y_top =" in l or "y_bottom =" in l or "p_h =" in l else "normal"
            fc = BLUE_ACCENT if fw == "bold" else GRAY_BODY
            ax.text(0.90, y_pos, l, fontsize=7.8, color=fc, fontweight=fw)
            y_pos -= 0.18
        y_pos -= 0.08

    # Summary box at bottom of left card
    draw_card(ax, 0.85, 0.80, 6.10, 0.90, bg="#F0FDF4", border="#86EFAC")
    ax.text(1.05, 1.45, "ANATOMICAL ACCURACY GUARANTEE", fontsize=8.2, fontweight="bold", color=GREEN_PASS)
    ax.text(1.05, 1.20, "- Eliminates chin-tilt variance (+/-15 cm error) by anchoring apex to YOLOv8 box.", fontsize=7.6, color=NAVY_DARK)
    ax.text(1.05, 0.98, "- Bilateral 4-point foot check avoids ground ambiguity, ensuring true physical stature p_h.", fontsize=7.6, color=NAVY_DARK)

    # Right Card: Visual Coordinate Schematic
    draw_card(ax, 7.50, 0.60, 5.23, 5.60, bg="#F1F5F9", border="#CBD5E1")
    draw_badge(ax, 7.80, 5.80, "COORDINATE SCHEMATIC", bg=BLUE_ACCENT)
    ax.text(7.80, 5.35, "Vertical Coordinate Rays", fontsize=13, fontweight="bold", color=NAVY_DARK)
    
    # Draw stick figure with coordinate lines
    cx = 10.10
    # Head apex line (Red)
    ax.plot([cx - 1.6, cx + 1.6], [4.60, 4.60], color=RED_ERR, lw=2.5, ls="--")
    ax.text(cx + 1.7, 4.60, "Cranial Apex (y_top)", color=RED_ERR, fontsize=8.5, fontweight="bold", va="center")
    
    # Head circle
    head = plt.Circle((cx, 4.15), 0.35, color=TEAL, fill=False, lw=2.5)
    ax.add_patch(head)
    
    # Torso & Shoulders
    ax.plot([cx - 0.7, cx + 0.7], [3.65, 3.65], color=NAVY_HEADER, lw=3) # shoulders
    ax.plot([cx, cx], [3.65, 2.45], color=NAVY_HEADER, lw=3) # spine
    ax.plot([cx - 0.5, cx + 0.5], [2.45, 2.45], color=NAVY_HEADER, lw=3) # hips
    
    # Limbs
    ax.plot([cx - 0.7, cx - 1.0, cx - 1.1], [3.65, 2.95, 2.25], color=NAVY_HEADER, lw=2) # Left arm
    ax.plot([cx + 0.7, cx + 1.0, cx + 1.1], [3.65, 2.95, 2.25], color=NAVY_HEADER, lw=2) # Right arm
    
    ax.plot([cx - 0.5, cx - 0.5, cx - 0.6], [2.45, 1.75, 1.15], color=NAVY_HEADER, lw=2.5) # Left leg
    ax.plot([cx + 0.5, cx + 0.5, cx + 0.6], [2.45, 1.75, 1.15], color=NAVY_HEADER, lw=2.5) # Right leg
    
    # Ground plane line (Green)
    ax.plot([cx - 1.6, cx + 1.6], [1.15, 1.15], color=GREEN_PASS, lw=2.5, ls="--")
    ax.text(cx + 1.7, 1.15, "Ground Contact (y_bottom)", color=GREEN_PASS, fontsize=8.5, fontweight="bold", va="center")
    
    # Height Ray (Double-headed arrow)
    ax.annotate("", xy=(cx - 1.3, 4.60), xytext=(cx - 1.3, 1.15),
                arrowprops=dict(arrowstyle="<->", color=BLUE_ACCENT, lw=2.5))
    ax.text(cx - 1.45, 2.85, "Pixel Stature p_h", color=BLUE_ACCENT, fontsize=8.5, fontweight="bold", 
            ha="right", va="center", rotation=90)
    
    # Keypoint labels
    ax.scatter([cx - 0.7, cx + 0.7, cx - 0.5, cx + 0.5], [3.65, 3.65, 2.45, 2.45], color=CYAN_ACCENT, s=40, zorder=5)
    ax.scatter([cx - 0.6, cx + 0.6], [1.15, 1.15], color=GREEN_PASS, s=50, zorder=5)
    
    # Legend box at bottom
    draw_card(ax, 7.80, 0.70, 4.60, 0.35, bg=WHITE, border="#CBD5E1")
    ax.text(10.10, 0.87, "Key: Red = Apex | Green = Ground Contact | Cyan = Joints", fontsize=7.8, color=NAVY_DARK, ha="center", va="center", fontweight="bold")

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 6: LIVE VISUAL PROOF - SAMPLE IMAGE INSPECTION
# ==============================================================================
def make_slide_6(pdf):
    fig, ax = create_slide_base("Live Visual Proof: Sample Image Inspection from Dataset", slide_num=6)
    
    # Left Box: Image Frame
    draw_card(ax, 0.60, 0.60, 5.20, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "OPENCV VISUALIZER OVERLAY", bg=GREEN_PASS)
    ax.text(0.90, 5.35, "Participant In-Flight Inspection", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    # Embed actual annotated sample image if present
    if os.path.exists(SAMPLE_IMG_PATH):
        try:
            img = Image.open(SAMPLE_IMG_PATH)
            # Create subaxes for the image
            ax_img = fig.add_axes([0.08, 0.11, 0.32, 0.58])
            ax_img.imshow(img)
            ax_img.axis("off")
        except Exception as e:
            ax.text(3.20, 3.00, f"Image Preview:\n{e}", ha="center", va="center", color=GRAY_MUTED)
    else:
        ax.text(3.20, 3.00, "[Sample Annotated Image from model_specification/images]", ha="center", va="center")
        
    # Right Box: Visual Marking Breakdown
    draw_card(ax, 6.10, 0.60, 6.63, 5.60, bg=WHITE)
    draw_badge(ax, 6.40, 5.80, "PIPELINE VERIFICATION", bg=BLUE_ACCENT)
    ax.text(6.40, 5.35, "Dissecting Visual Overlays & Output Payload", fontsize=13, fontweight="bold", color=NAVY_DARK)
    
    breakdown = [
        ("1. Green Bounding Box (YOLOv8 Nano):", [
            "Encloses the detected subject with detection confidence (e.g. 'Person 92%').",
            "Isolates the target participant and discards background clutter."
        ]),
        ("2. Skeletal Wireframe (MediaPipe Pose Lite):", [
            "Connects 33 joints (shoulders, elbows, wrists, hips, knees, ankles).",
            "Enables real-time verification of standing posture and upright alignment."
        ]),
        ("3. Red Cranial Apex & Green Ground Rays:", [
            "Red horizontal line bounds the uppermost point of the cranium (y_top).",
            "Green horizontal line marks the lowest heel/toe floor contact (y_bottom).",
            "The vertical blue ray spans pixel stature p_h for pinhole optical geometry."
        ])
    ]
    
    y_pos = 4.85
    for title, lines in breakdown:
        ax.text(6.40, y_pos, title, fontsize=9.2, fontweight="bold", color=NAVY_DARK)
        y_pos -= 0.22
        for l in lines:
            ax.text(6.40, y_pos, l, fontsize=7.8, color=GRAY_BODY)
            y_pos -= 0.18
        y_pos -= 0.10

    # Highlight Card for Real Sample Output
    draw_card(ax, 6.35, 0.80, 6.13, 1.90, bg="#F0FDF4", border="#86EFAC")
    ax.text(6.55, 2.45, "REAL SAMPLE METRICS: PARTICIPANT SIVA (D = 150 cm, C = 100 cm)", 
            fontsize=8.8, fontweight="bold", color=GREEN_PASS)
    
    metrics_list = [
        ("Raw Uncalibrated Height (Pinhole):", "120.6 cm", "Suffers -39.4 cm optical deficit!"),
        ("Calibrated Stature (Ridge Engine):", "158.7 cm", "True: 160.0 cm -> Error: -1.3 cm (PASS)"),
        ("Predicted Body Weight (Ridge):", "60.5 kg", "True: 62.0 kg -> Error: -1.5 kg (PASS)"),
        ("Calculated BMI & Triage Tier:", "24.0 kg/m^2", "Clinically Normal Weight (WHO Match)")
    ]
    
    y_m = 2.15
    for label, val, note in metrics_list:
        ax.text(6.55, y_m, label, fontsize=8, fontweight="bold", color=NAVY_DARK)
        ax.text(9.30, y_m, val, fontsize=8, fontweight="bold", color=BLUE_ACCENT)
        ax.text(10.20, y_m, f"({note})", fontsize=7.5, color=GRAY_BODY)
        y_m -= 0.34

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 7: BODY PROPORTION & 8 ANTHROPOMETRIC FEATURES (FIXED OVERLAP)
# ==============================================================================
def make_slide_7(pdf):
    fig, ax = create_slide_base("Body Proportion Engineering: The 8 Scale-Invariant Proxies", slide_num=7)
    
    # Intro Banner at top
    draw_card(ax, 0.60, 5.25, 12.13, 0.90, bg="#F1F5F9", border="#CBD5E1")
    draw_badge(ax, 0.90, 5.85, "WHY SCALE-INVARIANT RATIOS?", bg=BLUE_ACCENT)
    ax.text(3.70, 5.85, "Dividing transverse measurements by vertical pixel stature p_h cancels camera distance D.", fontsize=8.5, color=NAVY_DARK, va="center")
    ax.text(0.90, 5.48, "Raw pixel counts change drastically with distance. Dimensionless ratios yield somatic proxies invariant to standoff depth.",
            fontsize=8.2, color=GRAY_BODY)
    
    # 8 Feature Cards (2x4 Grid)
    # Row 2 (top row): y = 2.95, h = 2.05 (top is 5.00, gap to banner is 0.25)
    # Row 1 (bottom row): y = 0.65, h = 2.05 (bottom is 0.65, gap between rows is 0.25)
    feats = [
        ("x1: Calibrated Stature (H_cal)", "H_cal = w^T z + b", "Metric height in cm derived from Ridge calibrator. Sets overall volumetric envelope."),
        ("x2: Bi-Acromial Ratio (w_sh/p_h)", "w_sh / p_h", "Shoulder joint span divided by pixel stature. Quantifies upper skeletal frame breadth."),
        ("x3: Bi-Iliac Ratio (w_hip/p_h)", "w_hip / p_h", "Pelvic hip joint span divided by pixel stature. Quantifies lower pelvic skeletal build."),
        ("x4: Silhouette Fill Factor", "sum(M) / (w * h)", "Ratio of body mask pixels to full box area. Captures muscular density and somatic corpulence."),
        ("x5: Bounding Aspect Ratio", "w_box / h_box", "Ratio of bounding box width to height. Distinguishes between slender and stocky builds."),
        ("x6: Chest Cross-Section", "n_0.30 / p_h", "Foreground mask width sampled at 30% torso depth. Non-contact proxy for chest circumference."),
        ("x7: Waist Cross-Section", "n_0.52 / p_h", "Foreground mask width sampled at 52% torso depth. Non-contact proxy for waist circumference."),
        ("x8: Lower Torso Slice", "n_0.70 / p_h", "Foreground mask width sampled at 70% torso depth. Non-contact proxy for hip circumference.")
    ]
    
    grid_coords = [
        (0.60, 2.95), (3.69, 2.95), (6.78, 2.95), (9.87, 2.95),
        (0.60, 0.65), (3.69, 0.65), (6.78, 0.65), (9.87, 0.65)
    ]
    
    for idx, (ftitle, fformula, fdesc) in enumerate(feats):
        gx, gy = grid_coords[idx]
        draw_card(ax, gx, gy, 2.85, 2.05, bg=WHITE)
        draw_badge(ax, gx + 0.15, gy + 1.78, f"FEATURE {idx+1}", bg=TEAL if idx < 5 else BLUE_ACCENT, fontsize=7.5)
        ax.text(gx + 0.15, gy + 1.48, ftitle, fontsize=8.2, fontweight="bold", color=NAVY_DARK)
        
        # Formula tag
        ax.text(gx + 0.15, gy + 1.25, fformula, fontsize=7.8, fontweight="bold", color=BLUE_ACCENT, fontfamily="monospace")
        
        # Split description into clean lines
        words = fdesc.split()
        lines = []
        cur_line = []
        for w in words:
            cur_line.append(w)
            if len(" ".join(cur_line)) > 26:
                lines.append(" ".join(cur_line))
                cur_line = []
        if cur_line:
            lines.append(" ".join(cur_line))
            
        ly = gy + 0.95
        for l in lines:
            ax.text(gx + 0.15, ly, l, fontsize=7.2, color=GRAY_BODY)
            ly -= 0.18

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 8: PINHOLE OPTICAL GEOMETRY & PITCH COMPENSATION
# ==============================================================================
def make_slide_8(pdf):
    fig, ax = create_slide_base("Pinhole Optical Projection Geometry & Camera Pitch Recovery", slide_num=8)
    
    # Left Card: Geometry Diagram
    draw_card(ax, 0.60, 0.60, 5.85, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "OPTICAL RAY-TRACING", bg=BLUE_ACCENT)
    ax.text(0.90, 5.35, "Monocular Geometric Ray Formulation", fontsize=13, fontweight="bold", color=NAVY_DARK)
    
    # Draw Pinhole Ray Diagram
    cam_x, cam_y = 1.30, 3.50
    # Camera box
    ax.plot([cam_x-0.3, cam_x+0.3, cam_x+0.3, cam_x-0.3, cam_x-0.3], [cam_y-0.4, cam_y-0.4, cam_y+0.4, cam_y+0.4, cam_y-0.4], color=NAVY_HEADER, lw=2)
    ax.text(cam_x, cam_y-0.65, "Camera Lens\n(Mount Height C)", fontsize=7.5, color=NAVY_DARK, ha="center")
    
    # Floor line
    floor_y = 1.20
    ax.plot([cam_x - 0.5, 6.00], [floor_y, floor_y], color="#94A3B8", lw=2)
    ax.text(1.20, floor_y - 0.25, "Floor Plane (Ground Level)", fontsize=7.5, color=GRAY_MUTED)
    
    # Subject at distance D
    sub_x = 5.00
    sub_top = 4.80
    sub_bot = floor_y
    # Draw Subject
    ax.plot([sub_x, sub_x], [sub_bot, sub_top], color=TEAL, lw=4)
    ax.scatter([sub_x], [sub_top], color=RED_ERR, s=60, zorder=5) # Head
    ax.scatter([sub_x], [sub_bot], color=GREEN_PASS, s=60, zorder=5) # Feet
    ax.text(sub_x, sub_top + 0.20, "Cranial Apex", color=RED_ERR, fontsize=7.5, fontweight="bold", ha="center")
    ax.text(sub_x, sub_bot - 0.25, "Ground Contact", color=GREEN_PASS, fontsize=7.5, fontweight="bold", ha="center")
    
    # Optical Rays
    ax.plot([cam_x+0.3, sub_x], [cam_y, sub_top], color=RED_ERR, ls="--", lw=1.5) # Head ray
    ax.plot([cam_x+0.3, sub_x], [cam_y, sub_bot], color=GREEN_PASS, ls="--", lw=1.5) # Foot ray
    ax.plot([cam_x+0.3, sub_x], [cam_y, cam_y], color=GRAY_MUTED, ls=":", lw=1.2) # Optical axis
    
    # Distance arrow
    ax.annotate("", xy=(sub_x, 1.50), xytext=(cam_x, 1.50), arrowprops=dict(arrowstyle="<->", color=BLUE_ACCENT, lw=2))
    ax.text((cam_x + sub_x)/2, 1.65, "Standoff Distance D", fontsize=8.5, color=BLUE_ACCENT, fontweight="bold", ha="center")
    
    # Height arrow
    ax.annotate("", xy=(sub_x + 0.35, sub_top), xytext=(sub_x + 0.35, sub_bot), arrowprops=dict(arrowstyle="<->", color=TEAL, lw=2))
    ax.text(sub_x + 0.50, (sub_top + sub_bot)/2, "True Height H", fontsize=8.5, color=TEAL, fontweight="bold", rotation=90, va="center")

    # Right Card: Mathematical Formulas
    draw_card(ax, 6.75, 0.60, 5.98, 5.60, bg=WHITE)
    draw_badge(ax, 7.05, 5.80, "DERIVATION FORMULAS", bg=TEAL)
    ax.text(7.05, 5.35, "Deterministic Mathematical Derivation", fontsize=13, fontweight="bold", color=NAVY_DARK)
    
    f_steps = [
        ("1. Vertical Focal Length (f_y in Pixels):",
         "f_y = (H_I / 2) / tan(v / 2)\nwhere H_I is image pixel height, v = 55.0 deg (standard FOV)."),
        ("2. Angular Elevations of Head & Feet:",
         "alpha_t = arctan( (H_I/2 - y_top) / f_y )\nalpha_b = arctan( (H_I/2 - y_bottom) / f_y )"),
        ("3. Nominal Ground Depression Angle (theta_b):",
         "theta_b = -arctan( C / D )\nwhere C = Camera Mount Height (100 cm), D = Distance (150 cm)."),
        ("4. Camera Pitch Angle Recovery (theta):",
         "theta = theta_b - alpha_b\nRecovers true smartphone tilt relative to the floor horizon!"),
        ("5. Absolute Cranial Elevation (phi_t):",
         "phi_t = theta + alpha_t\nTrue optical ray angle aimed at the person's cranial vertex."),
        ("6. Raw Uncalibrated Height (H_g):",
         "H_g = max(0, C + D * tan(phi_t))\nProvides deterministic geometric height before learned calibration.")
    ]
    
    y_math = 4.90
    for title, formula in f_steps:
        ax.text(7.05, y_math, title, fontsize=8.8, fontweight="bold", color=NAVY_DARK)
        y_math -= 0.20
        for fl in formula.split("\n"):
            ax.text(7.25, y_math, fl, fontsize=7.8, color=BLUE_ACCENT if "=" in fl else GRAY_BODY, fontfamily="monospace" if "=" in fl else "sans-serif")
            y_math -= 0.17
        y_math -= 0.08

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 9: STATISTICAL METRICS DEMYSTIFIED (FIXED HORIZONTAL OVERFLOW)
# ==============================================================================
def make_slide_9(pdf):
    fig, ax = create_slide_base("Statistical Metrics Demystified: Core Viva Evaluation Concepts", slide_num=9)
    
    metrics = [
        ("MAE (Mean Absolute Error)", BLUE_ACCENT,
         "MAE = (1/N) * sum(|y_i - y_hat_i|)",
         "Average error magnitude in physical units (cm or kg).",
         "Treats all deviations equally; easy clinical interpretation.",
         "Height: 4.14 cm | Weight: 7.28 kg (Front), 6.47 kg (Fused)"),
        
        ("RMSE (Root Mean Squared Error)", TEAL,
         "RMSE = sqrt((1/N) * sum((y_i - y_hat_i)^2))",
         "Heavily penalizes isolated large outlier errors.",
         "RMSE close to MAE proves zero severe catastrophic blunders.",
         "Height RMSE: 5.07 cm (Close to MAE 4.14 cm -> Stable!)"),
        
        ("Bias (Mean Signed Error)", AMBER_WARN,
         "Bias = (1/N) * sum(y_hat_i - y_i)",
         "Shows systematic OVERESTIMATION (+) or UNDERESTIMATION (-).",
         "Raw pinhole had fatal -36.58 cm bias; Ridge corrected it.",
         "Height Bias: +0.63 cm | Weight Bias: +0.47 kg (Neutral)"),
        
        ("R^2 (Coefficient of Determination)", CYAN_ACCENT,
         "R^2 = 1 - (SS_res / SS_tot)",
         "Proportion of true cohort variance explained (max 1.0).",
         "Negative R^2 means worse than predicting the cohort mean.",
         "Raw Pinhole: -21.56 (Terrible) -> Calibrated: +0.576 (Good)"),
        
        ("Pearson Correlation Coefficient (r)", NAVY_HEADER,
         "r = Cov(y, y_hat) / (sigma_y * sigma_y_hat)",
         "Measures linear association strength (-1 to +1).",
         "r > 0.70 represents strong positive linear alignment.",
         "Height Pearson r: 0.785 | Weight Pearson r: 0.768 (Strong)"),
        
        ("Median vs. Mean Cohort Baseline", RED_ERR,
         "Fold Baseline = Median(Y_train)",
         "Predicting the median without inspecting the image.",
         "Validates that ML models truly learn beyond chance.",
         "Calibrator beats baseline by 42% (Height) & 35% (Weight)")
    ]
    
    coords = [
        (0.60, 3.45), (4.70, 3.45), (8.80, 3.45),
        (0.60, 0.65), (4.70, 0.65), (8.80, 0.65)
    ]
    
    for idx, (m_name, m_color, m_formula, m_mean, m_why, m_res) in enumerate(metrics):
        x, y = coords[idx]
        draw_card(ax, x, y, 3.93, 2.65, bg=WHITE)
        draw_badge(ax, x + 0.15, y + 2.35, f"CONCEPT {idx+1}", bg=m_color, fontsize=7.5)
        ax.text(x + 0.15, y + 1.98, m_name, fontsize=8.8, fontweight="bold", color=NAVY_DARK)
        
        # Formula box
        draw_card(ax, x + 0.15, y + 1.55, 3.63, 0.32, bg="#F1F5F9", border="#E2E8F0")
        ax.text(x + 0.25, y + 1.71, m_formula, fontsize=7.5, fontweight="bold", color=BLUE_ACCENT, fontfamily="monospace", va="center")
        
        ax.text(x + 0.15, y + 1.30, f"- Meaning: {m_mean}", fontsize=7.4, color=GRAY_BODY)
        ax.text(x + 0.15, y + 0.95, f"- Importance: {m_why}", fontsize=7.4, color=GRAY_BODY)
        
        # Result box
        draw_card(ax, x + 0.15, y + 0.20, 3.63, 0.55, bg="#ECFDF5", border="#A7F3D0")
        ax.text(x + 0.25, y + 0.58, "Our Benchmark Result:", fontsize=7.2, fontweight="bold", color=GREEN_PASS)
        ax.text(x + 0.25, y + 0.35, m_res, fontsize=7.4, fontweight="bold", color=NAVY_DARK)

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 10: THE "CALIBRATION THING" - WHY RAW PHYSICS FAILS
# ==============================================================================
def make_slide_10(pdf):
    fig, ax = create_slide_base("What is the 'Calibration Thing'? Why Pure Physics Underestimates Height", slide_num=10)
    
    # Left Card: The Problem with Raw Pinhole
    draw_card(ax, 0.60, 0.60, 5.85, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "THE PHYSICAL DEFICIT", bg=RED_ERR)
    ax.text(0.90, 5.35, "Why Raw Pinhole Underestimates by ~36 cm", fontsize=13, fontweight="bold", color=NAVY_DARK)
    
    reasons = [
        ("Factor 1: Mobile Lens Radial Barrel Distortion", [
            "Consumer smartphone wide-angle lenses possess barrel distortion.",
            "Rays bend inward at image perimeters, compressing apparent vertical",
            "pixel span p_h, which artificially truncates computed metric height."
        ]),
        ("Factor 2: Nominal FOV vs. Real Sensor Crop Mismatch", [
            "We assume a default nominal 55.0 deg vertical field of view (FOV).",
            "In practice, mobile sensor aspect ratios (4:3 vs 16:9), digital stabilization,",
            "and manufacturing variances cause effective FOV to deviate by +/- 3 deg.",
            "Even a 2 deg error in FOV propagates into 15 to 25 cm of height error!"
        ]),
        ("Factor 3: Foot-Plane Keypoint & Shoe Margin Offset", [
            "MediaPipe ankle and heel keypoints detect the skeletal bone joint.",
            "This joint naturally sits 3 to 6 cm ABOVE the actual floor plane!",
            "Furthermore, subjects wear shoes with rubber soles that elevate them.",
            "This results in ground elevation alpha_b being measured too high."
        ])
    ]
    
    y_pos = 4.90
    for title, lines in reasons:
        ax.text(0.90, y_pos, title, fontsize=9.2, fontweight="bold", color=NAVY_DARK)
        y_pos -= 0.22
        for l in lines:
            ax.text(0.90, y_pos, l, fontsize=7.8, color=GRAY_BODY)
            y_pos -= 0.18
        y_pos -= 0.12

    # Right Card: How Learned Ridge Calibration Solves It
    draw_card(ax, 6.75, 0.60, 5.98, 5.60, bg=WHITE)
    draw_badge(ax, 7.05, 5.80, "THE MACHINE LEARNING FIX", bg=GREEN_PASS)
    ax.text(7.05, 5.35, "The Learned L2 Ridge Calibrator", fontsize=13, fontweight="bold", color=NAVY_DARK)
    
    sol = [
        ("The Ridge Calibration Formulation:", [
            "Instead of guessing manual offset constants, we train an L2-regularized",
            "Ridge model: min sum (y_i - w^T z_i - b)^2 + alpha ||w||_2^2",
            "z_i incorporates raw height H_g and scaled anthropometric ratios.",
            "Hyperparameter alpha = 0.1 was tuned via participant-grouped cross-validation."
        ]),
        ("Quantitative Error Reduction Impact:", [
            "- Raw Pinhole Height MAE:   36.58 cm  (Bias: -36.58 cm, R^2 = -21.56)",
            "- Fold Median Baseline MAE:  7.11 cm  (Bias: +1.24 cm, R^2 = -0.21)",
            "- Calibrated Ridge MAE:      4.14 cm  (Bias: +0.63 cm, R^2 = +0.576)"
        ]),
        ("Key Viva Takeaway for Your Team:", [
            "We achieved an 88.7% ERROR REDUCTION over raw optical geometry!",
            "The calibrator doesn't replace physics; it learns the systematic lens distortion",
            "and joint-floor offset transfer function to bridge theory with reality."
        ])
    ]
    
    y_s = 4.90
    for title, lines in sol:
        ax.text(7.05, y_s, title, fontsize=9.2, fontweight="bold", color=NAVY_DARK)
        y_s -= 0.22
        for l in lines:
            color = GREEN_PASS if "4.14 cm" in l or "88.7% ERROR" in l else GRAY_BODY
            fw = "bold" if color == GREEN_PASS else "normal"
            ax.text(7.05, y_s, l, fontsize=7.8, color=color, fontweight=fw)
            y_s -= 0.18
        y_s -= 0.14

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 11: GRAPH BREAKDOWN - BENCHMARKS & CORRELATION PARITY
# ==============================================================================
def make_slide_11(pdf):
    fig, ax = create_slide_base("Graph Breakdown: Comparative MAE Benchmarks & Weight Parity Plot", slide_num=11)
    
    # Left Half: Fig 3 Comparative Bar Charts
    draw_card(ax, 0.60, 0.60, 5.85, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "GRAPH 1: FIGURE 3 WALKTHROUGH", bg=BLUE_ACCENT)
    ax.text(0.90, 5.35, "Comparative MAE Bar Charts (Height & Weight)", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    # Render Bar Charts inside left card
    ax_bar1 = fig.add_axes([0.08, 0.22, 0.18, 0.38])
    ax_bar2 = fig.add_axes([0.28, 0.22, 0.14, 0.38])
    
    # Height bars
    h_labels = ["Pinhole", "Baseline", "Ridge"]
    h_vals = [36.58, 7.11, 4.14]
    h_colors = [RED_ERR, AMBER_WARN, BLUE_ACCENT]
    bars1 = ax_bar1.bar(h_labels, h_vals, color=h_colors, width=0.55)
    ax_bar1.set_ylabel("Height MAE (cm)", fontsize=8, fontweight="bold")
    ax_bar1.set_ylim(0, 42)
    ax_bar1.tick_params(labelsize=7.5)
    for b in bars1:
        ax_bar1.text(b.get_x() + b.get_width()/2, b.get_height() + 1, f"{b.get_height():.1f}", ha="center", fontsize=7.5, fontweight="bold")
        
    # Weight bars
    w_labels = ["Baseline", "Ridge"]
    w_vals = [11.22, 7.28]
    w_colors = [AMBER_WARN, BLUE_ACCENT]
    bars2 = ax_bar2.bar(w_labels, w_vals, color=w_colors, width=0.50)
    ax_bar2.set_ylabel("Weight MAE (kg)", fontsize=8, fontweight="bold")
    ax_bar2.set_ylim(0, 15)
    ax_bar2.tick_params(labelsize=7.5)
    for b in bars2:
        ax_bar2.text(b.get_x() + b.get_width()/2, b.get_height() + 0.4, f"{b.get_height():.1f}", ha="center", fontsize=7.5, fontweight="bold")
        
    ax.text(0.90, 1.05, "Takeaway: Ridge Calibrator achieves 88.7% height error reduction.\nRidge Regressor cuts weight error by 35.1% over fold median baseline.", 
            fontsize=8.2, color=NAVY_DARK, fontweight="bold")

    # Right Half: Fig 4 Weight Parity Correlation Scatter Plot
    draw_card(ax, 6.75, 0.60, 5.98, 5.60, bg=WHITE)
    draw_badge(ax, 7.05, 5.80, "GRAPH 2: FIGURE 4 WALKTHROUGH", bg=TEAL)
    ax.text(7.05, 5.35, "Correlation Parity Scatter Plot (R^2 = 0.560, r = 0.768)", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    ax_scat = fig.add_axes([0.55, 0.22, 0.38, 0.38])
    pts = [
        (56.0,59.28),(87.0,69.34),(55.0,57.09),(46.0,56.77),(68.0,69.48),
        (45.0,49.20),(51.0,56.95),(76.0,71.58),(65.0,68.69),(50.0,55.01),
        (64.0,65.29),(50.0,61.68),(69.0,61.65),(74.0,79.04),(75.0,69.43),
        (81.0,73.49),(80.0,77.61),(68.0,62.65),(65.0,74.63),(74.0,67.65),
        (67.0,70.99),(77.0,67.07),(90.0,73.80),(81.0,71.52),(76.0,75.09),
        (61.0,61.77),(76.0,77.03),(54.5,66.01),(90.0,83.39),(71.0,79.39),
        (60.0,73.24),(90.0,78.91),(50.0,64.11),(50.0,57.25),(69.0,67.73),
        (87.0,73.12),(55.0,73.88)
    ]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    ax_scat.scatter(xs, ys, color=BLUE_ACCENT, s=28, alpha=0.85, edgecolors=NAVY_DARK, lw=0.8)
    ax_scat.plot([40, 95], [40, 95], color=GRAY_MUTED, ls="--", lw=1.5, label="Ideal Parity y = x")
    ax_scat.set_xlabel("Measured Ground-Truth Weight (kg)", fontsize=8, fontweight="bold")
    ax_scat.set_ylabel("Predicted Weight (kg)", fontsize=8, fontweight="bold")
    ax_scat.set_xlim(40, 95)
    ax_scat.set_ylim(40, 95)
    ax_scat.tick_params(labelsize=7.5)
    ax_scat.legend(loc="upper left", fontsize=7.5)
    
    ax.text(7.05, 1.05, "Takeaway: Predictions cluster tightly along the diagonal identity line.\nAt >85 kg, L2 shrinkage prevents variance explosion on rare heavy builds.", 
            fontsize=8.2, color=NAVY_DARK, fontweight="bold")

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 12: MULTI-VIEW CORONAL-SAGITTAL FUSION
# ==============================================================================
def make_slide_12(pdf):
    fig, ax = create_slide_base("Multi-View Coronal-Sagittal Fusion: 2D Silhouettes to 3D Mass", slide_num=12)
    
    # Top Card: Physical Theory
    draw_card(ax, 0.60, 4.35, 12.13, 1.85, bg=WHITE)
    draw_badge(ax, 0.90, 5.85, "THE VOLUMETRIC MECHANISM", bg=BLUE_ACCENT)
    ax.text(0.90, 5.45, "Why Fusing Coronal (Front) and Sagittal (Side) Views Drops Error", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    ax.text(0.90, 5.05, "- Coronal (Front View): Captures shoulder breadth, waist width, and lateral leg contour (X-axis breadth). Zero depth info (Z-axis).", fontsize=8.5, color=GRAY_BODY)
    ax.text(0.90, 4.75, "- Sagittal (Side View): Captures anterior-posterior depth, abdominal protrusion, and lordotic curvature (Z-axis depth). Zero shoulder breadth.", fontsize=8.5, color=GRAY_BODY)
    ax.text(0.90, 4.45, "- Mathematical Cylinder Approximation: Human Torso Volume V is proportional to X * Z * H. Dual-view convex fusion estimates true 3D mass!", fontsize=8.5, fontweight="bold", color=TEAL)

    # Bottom Left: Table III Empirical Results
    draw_card(ax, 0.60, 0.60, 5.85, 3.55, bg=WHITE)
    draw_badge(ax, 0.90, 3.85, "TABLE III EMPIRICAL BENCHMARK", bg=TEAL)
    ax.text(0.90, 3.45, "Ablation Across 28 Paired Participant Groups", fontsize=11, fontweight="bold", color=NAVY_DARK)
    
    t_rows = [
        ("Viewpoint Config", "MAE (kg)", "RMSE (kg)", "R^2", "Bias (kg)"),
        ("Side View Only (W_side)", "8.05", "9.61", "0.441", "+1.45"),
        ("Front View Only (W_front)", "7.00", "8.10", "0.603", "+0.37"),
        ("Fused Dual-View (W_fused)", "6.47", "7.94", "0.618", "+0.91")
    ]
    
    y_tr = 3.05
    for r_idx, (c1, c2, c3, c4, c5) in enumerate(t_rows):
        bg_col = "#E2E8F0" if r_idx == 0 else ("#CCFBF1" if r_idx == 3 else WHITE)
        fw = "bold" if r_idx in (0, 3) else "normal"
        fg_col = TEAL if r_idx == 3 else NAVY_DARK
        
        row_box = patches.Rectangle((0.80, y_tr - 0.18), 5.40, 0.38, facecolor=bg_col, edgecolor="#CBD5E1", lw=0.8)
        ax.add_patch(row_box)
        
        ax.text(0.90, y_tr, c1, fontsize=8, fontweight=fw, color=fg_col, va="center")
        ax.text(3.40, y_tr, c2, fontsize=8, fontweight=fw, color=fg_col, va="center", ha="center")
        ax.text(4.10, y_tr, c3, fontsize=8, fontweight=fw, color=fg_col, va="center", ha="center")
        ax.text(4.80, y_tr, c4, fontsize=8, fontweight=fw, color=fg_col, va="center", ha="center")
        ax.text(5.60, y_tr, c5, fontsize=8, fontweight=fw, color=fg_col, va="center", ha="center")
        y_tr -= 0.42

    # Bottom Right: Percentage Gains & Viva Talking Point
    draw_card(ax, 6.75, 0.60, 5.98, 3.55, bg="#F1F5F9", border="#CBD5E1")
    draw_badge(ax, 7.05, 3.85, "VIVA TALKING POINT", bg=AMBER_WARN)
    ax.text(7.05, 3.45, "Relative Gains from Multi-View Fusion", fontsize=11, fontweight="bold", color=NAVY_DARK)
    
    gains = [
        "- 7.5% Relative Error Reduction over Front-Only estimation (7.00 kg -> 6.47 kg).",
        "- 19.6% Relative Error Reduction over Side-Only estimation (8.05 kg -> 6.47 kg).",
        "- Explains why side-only has higher error: Side view lacks shoulder width,",
        "  which is the single most predictive feature for adult skeletal mass.",
        "- Convex fusion formula: W_fused = 0.5 * W_front + 0.5 * W_side.",
        "- Provides invigilators with clear mathematical proof of physical depth recovery!"
    ]
    y_g = 3.05
    for g in gains:
        ax.text(7.05, y_g, g, fontsize=8.2, color=NAVY_DARK if "Reduction" in g else GRAY_BODY,
                fontweight="bold" if "Reduction" in g else "normal")
        y_g -= 0.36

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 13: EMPIRICAL TABLES WALKTHROUGH (I TO IV)
# ==============================================================================
def make_slide_13(pdf):
    fig, ax = create_slide_base("Empirical Tables Walkthrough: System Configuration & Standoff Invariance", slide_num=13)
    
    # Left Card: Table I & Table II
    draw_card(ax, 0.60, 0.60, 5.85, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "TABLE I & II WALKTHROUGH", bg=BLUE_ACCENT)
    ax.text(0.90, 5.35, "Configuration & 5-Fold Benchmark (N=37 Groups)", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    ax.text(0.90, 4.90, "Table I: Runtime Configuration Parameters", fontsize=9.2, fontweight="bold", color=NAVY_DARK)
    ax.text(0.90, 4.65, "- Person Detector: YOLOv8 Nano (conf >= 0.40) | Pose: MediaPipe Lite (33 pts)", fontsize=7.8, color=GRAY_BODY)
    ax.text(0.90, 4.45, "- Camera Optics: Vertical FOV = 55.0 deg | Default Mount C = 100 cm | D = 150 cm", fontsize=7.8, color=GRAY_BODY)
    ax.text(0.90, 4.25, "- Regressors: Ridge (alpha=0.1 for Height, alpha=1.0 for Weight) | GroupKFold (k=5)", fontsize=7.8, color=GRAY_BODY)
    
    ax.text(0.90, 3.85, "Table II: Grouped Benchmark Results Summary", fontsize=9.2, fontweight="bold", color=NAVY_DARK)
    
    t2_rows = [
        ("Target / Method", "MAE", "RMSE", "R^2", "Bias"),
        ("Height: Raw Pinhole", "36.58 cm", "36.99 cm", "-21.56", "-36.58 cm"),
        ("Height: Median Baseline", "7.11 cm", "8.56 cm", "-0.21", "+1.24 cm"),
        ("Height: Ridge Calibrator", "4.14 cm", "5.07 cm", "0.576", "+0.63 cm"),
        ("Weight: Median Baseline", "11.22 kg", "13.35 kg", "-0.019", "+0.65 kg"),
        ("Weight: Ridge Regressor", "7.28 kg", "8.77 kg", "0.560", "+0.47 kg")
    ]
    y_t2 = 3.50
    for r_idx, (c1, c2, c3, c4, c5) in enumerate(t2_rows):
        bg_c = "#E2E8F0" if r_idx == 0 else ("#CCFBF1" if r_idx in (3, 5) else WHITE)
        fw = "bold" if r_idx in (0, 3, 5) else "normal"
        fg = TEAL if r_idx in (3, 5) else NAVY_DARK
        
        row_box = patches.Rectangle((0.80, y_t2 - 0.16), 5.40, 0.34, facecolor=bg_c, edgecolor="#CBD5E1", lw=0.6)
        ax.add_patch(row_box)
        ax.text(0.85, y_t2, c1, fontsize=7.4, fontweight=fw, color=fg, va="center")
        ax.text(3.45, y_t2, c2, fontsize=7.4, fontweight=fw, color=fg, va="center", ha="center")
        ax.text(4.15, y_t2, c3, fontsize=7.4, fontweight=fw, color=fg, va="center", ha="center")
        ax.text(4.80, y_t2, c4, fontsize=7.4, fontweight=fw, color=fg, va="center", ha="center")
        ax.text(5.55, y_t2, c5, fontsize=7.4, fontweight=fw, color=fg, va="center", ha="center")
        y_t2 -= 0.38

    ax.text(0.90, 1.05, "Leakage-Free Validation: All photos of a participant were strictly confined\nto EITHER training or testing fold. Identity leakage is completely zero!", fontsize=7.8, color=GREEN_PASS, fontweight="bold")

    # Right Card: Table IV Distance Invariance
    draw_card(ax, 6.75, 0.60, 5.98, 5.60, bg=WHITE)
    draw_badge(ax, 7.05, 5.80, "TABLE IV WALKTHROUGH", bg=TEAL)
    ax.text(7.05, 5.35, "Stratified Standoff Distance Invariance Analysis", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    t4_rows = [
        ("Standoff Distance", "Sample N", "Height MAE", "Weight MAE", "Height Bias"),
        ("D = 150 cm", "69 Images", "5.01 cm", "7.83 kg", "+0.55 cm"),
        ("D = 200 cm", "45 Images", "4.96 cm", "7.75 kg", "+0.18 cm"),
        ("Absolute Drift (Delta)", "---", "0.05 cm", "0.08 kg", "0.37 cm")
    ]
    y_t4 = 4.65
    for r_idx, (c1, c2, c3, c4, c5) in enumerate(t4_rows):
        bg_c = "#E2E8F0" if r_idx == 0 else ("#FEF3C7" if r_idx == 3 else WHITE)
        fw = "bold" if r_idx in (0, 3) else "normal"
        fg = AMBER_WARN if r_idx == 3 else NAVY_DARK
        
        row_box = patches.Rectangle((6.90, y_t4 - 0.20), 5.60, 0.40, facecolor=bg_c, edgecolor="#CBD5E1", lw=0.6)
        ax.add_patch(row_box)
        ax.text(7.00, y_t4, c1, fontsize=8, fontweight=fw, color=fg, va="center")
        ax.text(8.80, y_t4, c2, fontsize=8, fontweight=fw, color=fg, va="center", ha="center")
        ax.text(9.70, y_t4, c3, fontsize=8, fontweight=fw, color=fg, va="center", ha="center")
        ax.text(10.60, y_t4, c4, fontsize=8, fontweight=fw, color=fg, va="center", ha="center")
        ax.text(11.70, y_t4, c5, fontsize=8, fontweight=fw, color=fg, va="center", ha="center")
        y_t4 -= 0.48

    ax.text(7.05, 2.50, "Why This Table Impresses Invigilators:", fontsize=9.5, fontweight="bold", color=NAVY_DARK)
    t4_points = [
        "- When standoff distance changes from 150 cm to 200 cm (a 33% depth shift),",
        "  the height MAE changes by merely 0.05 cm (5.01 cm vs 4.96 cm)!",
        "- Weight MAE shifts by only 0.08 kg (7.83 kg vs 7.75 kg)!",
        "- Proves that our pinhole trigonometric formulation and normalized ratios",
        "  effectively eliminate distance-dependent pixel scaling.",
        "- Demonstrates robust scale invariance across real capture environments."
    ]
    y_t4p = 2.15
    for p in t4_points:
        ax.text(7.05, y_t4p, p, fontsize=8, color=GRAY_BODY)
        y_t4p -= 0.25

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 14: TABLES V TO VII - SENSITIVITY & CLINICAL TRIAGE (FIXED COLUMNS)
# ==============================================================================
def make_slide_14(pdf):
    fig, ax = create_slide_base("Empirical Sensitivity & Clinical Triage: Tables V, VI, and VII", slide_num=14)
    
    # Left Card: Table V (Sex & Illumination Sensitivity)
    draw_card(ax, 0.60, 0.60, 5.85, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "TABLE V WALKTHROUGH", bg=BLUE_ACCENT)
    ax.text(0.90, 5.35, "Sex Parity & Ambient Lighting Sensitivity", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    ax.text(0.90, 4.90, "Panel A: Sex-Stratified Demographic Breakdown", fontsize=9.2, fontweight="bold", color=NAVY_DARK)
    s_rows = [
        ("Demographic Cohort", "Count", "Height MAE", "Weight MAE", "Weight R^2"),
        ("Male Cohort (21 Grps)", "84", "4.22 cm", "7.41 kg", "0.548"),
        ("Female Cohort (16 Grps)", "67", "4.04 cm", "7.12 kg", "0.575"),
        ("Demographic Delta", "---", "0.18 cm", "0.29 kg", "0.027")
    ]
    y_s = 4.55
    for r_idx, (c1, c2, c3, c4, c5) in enumerate(s_rows):
        bg_c = "#E2E8F0" if r_idx == 0 else ("#FEF3C7" if r_idx == 3 else WHITE)
        fw = "bold" if r_idx in (0, 3) else "normal"
        row_box = patches.Rectangle((0.80, y_s - 0.16), 5.40, 0.34, facecolor=bg_c, edgecolor="#CBD5E1", lw=0.6)
        ax.add_patch(row_box)
        ax.text(0.85, y_s, c1, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center")
        ax.text(2.85, y_s, c2, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(3.75, y_s, c3, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(4.65, y_s, c4, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(5.60, y_s, c5, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        y_s -= 0.38
        
    ax.text(0.90, 2.75, "Panel B: Ambient Lighting Sensitivity (Lux)", fontsize=9.2, fontweight="bold", color=NAVY_DARK)
    l_rows = [
        ("Lighting Condition", "Count", "Height MAE", "Weight MAE", "Bias (cm)"),
        ("Daylight (400-600 lx)", "108", "4.08 cm", "7.18 kg", "+0.58 cm"),
        ("Dim Indoor (100-250 lx)", "43", "4.29 cm", "7.53 kg", "+0.76 cm"),
        ("Illumination Drift", "---", "0.21 cm", "0.35 kg", "0.18 cm")
    ]
    y_l = 2.40
    for r_idx, (c1, c2, c3, c4, c5) in enumerate(l_rows):
        bg_c = "#E2E8F0" if r_idx == 0 else ("#FEF3C7" if r_idx == 3 else WHITE)
        fw = "bold" if r_idx in (0, 3) else "normal"
        row_box = patches.Rectangle((0.80, y_l - 0.16), 5.40, 0.34, facecolor=bg_c, edgecolor="#CBD5E1", lw=0.6)
        ax.add_patch(row_box)
        ax.text(0.85, y_l, c1, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center")
        ax.text(2.85, y_l, c2, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(3.75, y_l, c3, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(4.65, y_l, c4, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(5.60, y_l, c5, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        y_l -= 0.38

    ax.text(0.90, 0.95, "Key Takeaway: Sex disparity is under 0.29 kg. Illumination drift is under 0.35 kg.\nProves our model generalizes across demographics and domestic lighting!", fontsize=7.8, color=GREEN_PASS, fontweight="bold")

    # Right Card: Table VI (Clinical BMI Confusion Matrix)
    draw_card(ax, 6.75, 0.60, 5.98, 5.60, bg=WHITE)
    draw_badge(ax, 7.05, 5.80, "TABLE VI & VII WALKTHROUGH", bg=TEAL)
    ax.text(7.05, 5.35, "Clinical BMI Classification & Tolerance Bands", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    ax.text(7.05, 4.90, "Table VI: Clinical BMI Confusion Matrix (151 Images)", fontsize=9.2, fontweight="bold", color=NAVY_DARK)
    bmi_rows = [
        ("Ground-Truth Class", "UW", "NW", "OW", "OB", "Recall"),
        ("Underweight (UW, N=14)", "11", "3", "0", "0", "78.6%"),
        ("Normal Weight (NW, N=86)", "4", "71", "11", "0", "82.6%"),
        ("Overweight (OW, N=38)", "0", "9", "28", "1", "73.7%"),
        ("Obese (OB, N=13)", "0", "0", "4", "9", "69.2%")
    ]
    y_bmi = 4.55
    for r_idx, (c1, c2, c3, c4, c5, c6) in enumerate(bmi_rows):
        bg_c = "#E2E8F0" if r_idx == 0 else WHITE
        fw = "bold" if r_idx == 0 else "normal"
        row_box = patches.Rectangle((6.90, y_bmi - 0.16), 5.60, 0.34, facecolor=bg_c, edgecolor="#CBD5E1", lw=0.6)
        ax.add_patch(row_box)
        ax.text(7.00, y_bmi, c1, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center")
        ax.text(9.20, y_bmi, c2, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(9.85, y_bmi, c3, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(10.50, y_bmi, c4, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(11.15, y_bmi, c5, fontsize=7.4, fontweight=fw, color=NAVY_DARK, va="center", ha="center")
        ax.text(11.95, y_bmi, c6, fontsize=7.4, fontweight=fw, color=TEAL if r_idx > 0 else NAVY_DARK, va="center", ha="center")
        y_bmi -= 0.38
        
    ax.text(7.05, 2.45, "Exact Category Agreement: 78.8% (119 / 151 images)", fontsize=8.5, fontweight="bold", color=GREEN_PASS)
    ax.text(7.05, 2.20, "Adjacent-Tier Agreement:  97.4% (147 / 151 images) -> ZERO severe blunders!", fontsize=8.5, fontweight="bold", color=BLUE_ACCENT)
    
    ax.text(7.05, 1.80, "Table VII: Cumulative Accuracy Tolerance Bands", fontsize=9.2, fontweight="bold", color=NAVY_DARK)
    ax.text(7.05, 1.50, "- Height Error <= 5.0 cm: 59.5% | Height Error <= 7.5 cm: 86.5%", fontsize=8, color=GRAY_BODY)
    ax.text(7.05, 1.25, "- Weight Error <= 5.0 kg: 35.1% | Weight Error <= 10.0 kg: 73.0%", fontsize=8, color=GRAY_BODY)
    ax.text(7.05, 0.95, "Proves reliable bounding for real-world remote telehealth screening!", fontsize=8, color=TEAL, fontweight="bold")

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 15: EDGE PERFORMANCE & RUNTIME LATENCY (TABLE IX)
# ==============================================================================
def make_slide_15(pdf):
    fig, ax = create_slide_base("Edge Profiling & Runtime Latency: Real-Time CPU Feasibility", slide_num=15)
    
    # Left Card: Table IX Breakdown
    draw_card(ax, 0.60, 0.60, 6.20, 5.60, bg=WHITE)
    draw_badge(ax, 0.90, 5.80, "TABLE IX LATENCY PROFILE", bg=BLUE_ACCENT)
    ax.text(0.90, 5.35, "End-to-End Pipeline Execution Time (CPU)", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    lat_rows = [
        ("Pipeline Sub-Stage", "Latency (ms)", "Fraction (%)"),
        ("1. Image Decode & Normalization", "3.2 ms", "5.2%"),
        ("2. YOLOv8 Nano Person Detection", "18.4 ms", "29.7%"),
        ("3. MediaPipe Pose Keypoints (33 pts)", "24.1 ms", "38.9%"),
        ("4. Selfie Silhouette Segmentation", "14.1 ms", "22.7%"),
        ("5. Pinhole Geometry & Feature Slicing", "2.2 ms", "3.5%"),
        ("6. Ridge Calibrator & Weight Regressor", "< 0.1 ms", "< 0.2%"),
        ("7. OpenCV Visualizer & Base64 Encode", "2.1 ms", "3.4%"),
        ("TOTAL END-TO-END EXECUTION", "62.0 ms", "100.0%"),
        ("EFFECTIVE SYSTEM THROUGHPUT", "16.1 FPS", "(Commodity CPU)")
    ]
    
    y_l = 4.80
    for r_idx, (c1, c2, c3) in enumerate(lat_rows):
        bg_c = "#E2E8F0" if r_idx == 0 else ("#CCFBF1" if r_idx in (7, 8) else WHITE)
        fw = "bold" if r_idx in (0, 7, 8) else "normal"
        fg = TEAL if r_idx in (7, 8) else NAVY_DARK
        
        row_box = patches.Rectangle((0.80, y_l - 0.16), 5.80, 0.35, facecolor=bg_c, edgecolor="#CBD5E1", lw=0.6)
        ax.add_patch(row_box)
        ax.text(0.90, y_l, c1, fontsize=8, fontweight=fw, color=fg, va="center")
        ax.text(4.40, y_l, c2, fontsize=8, fontweight=fw, color=fg, va="center", ha="center")
        ax.text(5.70, y_l, c3, fontsize=8, fontweight=fw, color=fg, va="center", ha="center")
        y_l -= 0.40

    ax.text(0.90, 0.95, "Key Takeaway: The entire AI pipeline finishes in 62.0 ms on standard CPU.\nNo expensive GPU acceleration required for interactive web usage!", fontsize=8, color=GREEN_PASS, fontweight="bold")

    # Right Card: Pie Chart & Architectural Analysis
    draw_card(ax, 7.10, 0.60, 5.63, 5.60, bg=WHITE)
    draw_badge(ax, 7.40, 5.80, "RUNTIME BOTTLENECK ANALYSIS", bg=TEAL)
    ax.text(7.40, 5.35, "Where Does the Time Go?", fontsize=12, fontweight="bold", color=NAVY_DARK)
    
    # Donut Chart
    ax_pie = fig.add_axes([0.56, 0.38, 0.36, 0.26])
    sizes = [29.7, 38.9, 22.7, 3.5, 0.2, 5.0]
    labels = ["YOLOv8", "Pose", "Segment", "Geom", "ML", "Other"]
    colors = [BLUE_ACCENT, TEAL, CYAN_ACCENT, AMBER_WARN, GREEN_PASS, "#94A3B8"]
    wedges, texts, autotexts = ax_pie.pie(sizes, labels=labels, autopct="%1.1f%%", pctdistance=0.75,
                                           colors=colors, startangle=140, textprops=dict(fontsize=7.5))
    centre_circle = plt.Circle((0, 0), 0.55, fc=WHITE)
    ax_pie.add_artist(centre_circle)
    ax_pie.axis("equal")
    
    ax.text(7.40, 2.30, "Critical Viva Defense Talking Points:", fontsize=9.2, fontweight="bold", color=NAVY_DARK)
    p_notes = [
        ("1. 91.3% of Latency is in Computer Vision Backbones:",
         "MediaPipe Pose (38.9%), YOLOv8 (29.7%), and Segmentation (22.7%)."),
        ("2. Machine Learning Inference Takes Sub-Milliseconds:",
         "Ridge regression requires matrix-vector product w^T x + b, executing in",
         "less than 100 microseconds (< 0.1 ms)! It is practically instantaneous."),
        ("3. Future Edge Export (ONNX / WebAssembly):",
         "Can be embedded directly inside client browsers for 100% offline edge execution.")
    ]
    y_pn = 2.05
    for p_title, *p_lines in p_notes:
        ax.text(7.40, y_pn, p_title, fontsize=8, fontweight="bold", color=NAVY_DARK)
        y_pn -= 0.18
        for pl in p_lines:
            ax.text(7.40, y_pn, pl, fontsize=7.6, color=GRAY_BODY)
            y_pn -= 0.17
        y_pn -= 0.08

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 16: SYSTEM OPERATIONAL LIMITATIONS & ERROR CAUSES (FIXED FOOTER OVERLAP)
# ==============================================================================
def make_slide_16(pdf):
    fig, ax = create_slide_base("Operational Limitations: Distance, Camera Height & Error Causes", slide_num=16)
    
    limits = [
        ("1. Subject Standoff Distance Limits (D)", AMBER_WARN, [
            "Valid Operating Envelope: 135 cm to 200 cm (Optimal: 150 cm).",
            "- If Distance < 130 cm: Subject is too close to camera; feet/head get clipped outside frame boundary.",
            "- If Distance > 250 cm: Subject appears too small (<500 px); landmark detector suffers jitter and edge blur."
        ]),
        ("2. Camera Mounting Height Limits (C)", BLUE_ACCENT, [
            "Valid Operating Envelope: 90 cm to 110 cm (Nominal: 100 cm, approx. waist/navel level).",
            "- Eye Level (160 cm): Looking down introduces extreme foreshortening, compressing apparent leg length.",
            "- Floor Level (30 cm): Looking up introduces perspective elongation, causing severe stature overestimation."
        ]),
        ("3. Clothing & Garment Boundary Effects", TEAL, [
            "Assumes Form-Fitting or Normal Everyday Clothing.",
            "- Loose parkas, heavy coats, or oversized hoodies artificially expand silhouette mask slices x6, x7, x8.",
            "- This causes weight overestimation by 4 to 8 kg. High-heeled shoes add artificial stature above biological height."
        ]),
        ("4. Posture & Environmental Lighting Constraints", RED_ERR, [
            "- Slouching / Knee Flexion: Reduces measured stature by 3 to 10 cm (guarded by theta_knee >= 160 deg).",
            "- Lighting Envelope: Validated between 100 and 600 lux. Below 80 lux (near darkness), keypoint extraction fails."
        ])
    ]
    
    # 4 cards strictly spaced between y = 4.80 and y = 0.75 (above footer 0.38)
    y_card = 4.80
    for title, color, points in limits:
        draw_card(ax, 0.60, y_card, 12.13, 1.22, bg=WHITE, border="#CBD5E1")
        draw_badge(ax, 0.90, y_card + 0.95, title, bg=color, fontsize=8.2)
        
        y_pt = y_card + 0.68
        for pt in points:
            fw = "bold" if pt.startswith("Valid") or pt.startswith("Assumes") or pt.startswith("- If") else "normal"
            fc = NAVY_DARK if fw == "bold" else GRAY_BODY
            ax.text(0.90, y_pt, pt, fontsize=8.0, color=fc, fontweight=fw)
            y_pt -= 0.19
        y_card -= 1.35

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# SLIDE 17: FINAL VIVA DEFENSE CHEAT-SHEET FOR THE TEAM (FIXED OVERLAP & Y-BOUNDS)
# ==============================================================================
def make_slide_17(pdf):
    fig, ax = create_slide_base("Final Viva Defense Cheat-Sheet: Top 5 Winning Answers for Your Team", slide_num=17)
    
    qa_pairs = [
        ("Q1: Why didn't you train an end-to-end deep neural network like ResNet for height & weight?",
         "End-to-end CNNs act as uninterpretable black boxes that overfit to clothing, textures, and lighting.",
         "Our decoupled approach combines deterministic projective optics with regularized ML, guaranteeing interpretability and data efficiency."),
        
        ("Q2: How did you prove your cross-validation didn't suffer from data leakage?",
         "We enforced strict 5-fold GroupKFold partitioned strictly by Participant ID.",
         "All photos of any participant were exclusively in train or test fold, eliminating identity and clothing leakage."),
        
        ("Q3: Why did raw pinhole camera geometry underestimate stature by ~36 cm?",
         "Three physical factors: (1) lens radial barrel distortion compressing apparent vertical pixels,",
         "(2) nominal 55 deg FOV crop factor mismatch, and (3) ankle keypoints detecting bone joints above true floor contact."),
        
        ("Q4: Why does dual-view fusion help weight estimation, but isn't needed for height?",
         "Height is a 1D vertical measurement fully visible in a single upright view.",
         "Weight is 3D physical mass; fusing coronal (breadth) and sagittal (depth) views recovers the 3D torso volume cylinder."),
        
        ("Q5: What are the main clinical takeaways of your research?",
         "Achieves 78.8% exact WHO BMI tier agreement and 97.4% adjacent-tier agreement with zero severe blunders,",
         "executing in 62 ms (~16.1 FPS) on commodity CPU, proving real-time feasibility for contactless telehealth intake.")
    ]
    
    # 5 cards strictly spaced between y = 4.95 and y = 0.75 (above footer 0.38)
    y_card = 4.95
    for idx, (q, line1, line2) in enumerate(qa_pairs):
        draw_card(ax, 0.60, y_card, 12.13, 0.98, bg=WHITE, border="#CBD5E1")
        
        # Question row
        ax.text(0.85, y_card + 0.74, q, fontsize=8.8, fontweight="bold", color=BLUE_ACCENT, va="center")
        
        # Winning Answer Badge
        draw_badge(ax, 0.85, y_card + 0.46, "WINNING ANSWER", bg=GREEN_PASS, fontsize=7.2)
        
        # Answer text lines (2 lines with generous spacing)
        ax.text(2.40, y_card + 0.46, line1, fontsize=7.8, color=NAVY_DARK, va="center")
        ax.text(0.85, y_card + 0.22, line2, fontsize=7.8, color=NAVY_DARK, va="center")
            
        y_card -= 1.05

    pdf.savefig(fig)
    plt.close(fig)

# ==============================================================================
# MAIN GENERATION PIPELINE
# ==============================================================================
def main():
    print(f"Starting generation of {OUTPUT_PDF}...")
    with PdfPages(OUTPUT_PDF) as pdf:
        print("Rendering Slide 1: Cover...")
        make_slide_1(pdf)
        print("Rendering Slide 2: Motivation & 3 Vision Challenges...")
        make_slide_2(pdf)
        print("Rendering Slide 3: 4-Stage Architecture Pipeline...")
        make_slide_3(pdf)
        print("Rendering Slide 4: Data Journey...")
        make_slide_4(pdf)
        print("Rendering Slide 5: How Body Markings Are Done...")
        make_slide_5(pdf)
        print("Rendering Slide 6: Live Sample Image Inspection...")
        make_slide_6(pdf)
        print("Rendering Slide 7: Body Proportion & 8 Features...")
        make_slide_7(pdf)
        print("Rendering Slide 8: Pinhole Geometry & Pitch Recovery...")
        make_slide_8(pdf)
        print("Rendering Slide 9: Statistical Metrics Demystified...")
        make_slide_9(pdf)
        print("Rendering Slide 10: The Calibration Thing...")
        make_slide_10(pdf)
        print("Rendering Slide 11: Graph Breakdown...")
        make_slide_11(pdf)
        print("Rendering Slide 12: Multi-View Coronal-Sagittal Fusion...")
        make_slide_12(pdf)
        print("Rendering Slide 13: Empirical Tables I to IV...")
        make_slide_13(pdf)
        print("Rendering Slide 14: Sensitivity & Clinical Triage...")
        make_slide_14(pdf)
        print("Rendering Slide 15: Edge Profiling & Latency Breakdown...")
        make_slide_15(pdf)
        print("Rendering Slide 16: Operational Limitations & Error Causes...")
        make_slide_16(pdf)
        print("Rendering Slide 17: Final Viva Defense Cheat-Sheet...")
        make_slide_17(pdf)
        
    fsize = os.path.getsize(OUTPUT_PDF)
    print(f"\n=======================================================")
    print(f"SUCCESS! {OUTPUT_PDF} successfully generated.")
    print(f"Total Slides: 17 widescreen 16:9 slides | File Size: {fsize / 1024:.1f} KB")
    print(f"=======================================================")

if __name__ == "__main__":
    main()
