## Standard Operating Procedure (Iterative Workflow)

### Phase 1: Extraction & Triage (Run this first)
1.  **Trigger Tool:** Call `prepare_video_for_analysis(video_filename)`.
2.  **Report Findings:** Once the tool finishes, look at the output structure (e.g., `stroke_1`, `stroke_2`).
3.  **STOP:** Do not analyze yet. Just tell the user: "Extraction complete. I found [X] stroke events. Please confirm you want me to proceed with the Deep Analysis."

### Phase 2: Deep Pattern Analysis (Run this after user confirmation)
1.  **Triage (The "Trash Filter"):**
    * Utilize your vision capabilities to Look at the **3rd image** in *every* `segment_X` folder.
    * **Decision Loop:**
        * If image shows a player walking/standing -> **IGNORE**.
        * If image shows a swing (racket blur/unit turn) -> **KEEP**.
    * *Internal Thought:* "Segment 1 is walking (Skip). Segment 2 is Forehand (Keep). Segment 3 is Backhand (Keep)."
    * **Utilize your vision capabilities to examine the frames in each kept stroke sequence.** This is the "Point of Contact" or peak swing.
    * *Decision:* Tag each stroke sequence as Forehand or Backhand based on the analysis of the "Point of Contact" or peak swing.
3.  **Forehand Analysis:**
    * For all Forehand-tagged sequences, utilize your vision capabilities to thoroughly examine ALL extracted frames in temp_frames/ and extract meaningful biomechanical information.
    * Identify consistent patterns across the frames (ignore one-off mistakes).
    * Manually fill the template with your analysis to create `analyses/report_forehand_[DATE].md`.
4.  **Backhand Analysis:**
    * For all Backhand-tagged sequences, utilize your vision capabilities to thoroughly examine ALL extracted frames in temp_frames/ and extract meaningful biomechanical information.
    * Identify consistent patterns across the frames (ignore one-off mistakes).
    * Manually fill the template with your analysis to create `analyses/report_backhand_[DATE].md`.
5.  **Publish:**
    * Run `generate_branded_pdf` for every Markdown file created.
