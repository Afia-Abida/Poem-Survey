import json
import random
from flask import Flask, render_template, request, redirect, url_for, flash, session
from sqlalchemy import func
from db import get_db
from models.models import Poem, Response, ResponseDraft, SurveySlot
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-fallback-key")

TOTAL_POEMS = 20

# --- ROUTES ---

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        email = request.form.get("email")
        if not email:
            flash("Please enter a valid email.", "danger")
            return redirect(url_for("home"))
        session["user_email"] = email
        return redirect(url_for("preliminaries"))
    return render_template("home.html")

@app.route("/preliminaries")
def preliminaries():
    if "user_email" not in session:
        return redirect(url_for("home"))
    return render_template("preliminaries.html")

# --- THE LOGIC CORE ---

@app.route("/survey")
def survey_start():
    if "user_email" not in session:
        return redirect(url_for("home"))
    
    email = session["user_email"]
    db = next(get_db())

    try:
        # 0. CHECK: If user already submitted, track completion from final `responses`
        response_count = db.query(func.count(Response.user_id)).filter_by(email=email).scalar() or 0
        if response_count >= TOTAL_POEMS:
            return redirect(url_for("thank_you"))

        # 1. CHECK: Does this user already have drafts?
        # We order by draft_id so we get them in the sequence they were created (1 to 20)
        existing_drafts = db.query(ResponseDraft).filter_by(email=email).order_by(ResponseDraft.draft_id).all()

        if existing_drafts:
            # --- RESUME LOGIC ---
            # Find the first draft that hasn't been answered (clarity is None)
            for index, draft in enumerate(existing_drafts):
                if draft.clarity is None:
                    # Redirect to that Question Number (Index + 1)
                    flash("Resuming your survey...", "info")
                    return redirect(url_for("survey_route", page_num=index + 1))
            
            # If all are answered, go to Thank You (or Review)
            return redirect(url_for("thank_you"))

        else:
            # --- NEW ASSIGNMENT LOGIC ---
            
            # A. Try to find an available GOLD slot (usage < 2)
            # We explicitly prioritize Gold slots for the first 14 users
            assigned_slot = db.query(SurveySlot).filter(
                SurveySlot.is_gold == 1, 
                SurveySlot.usage_count < 2
            ).first()

            # B. If no Gold available, find a Regular slot (usage < 2) - RANDOMLY
            # After user 14, regular slots are assigned randomly, not sequentially
            # Slots with usage_count = 0 and usage_count = 1 are both available randomly
            if not assigned_slot:
                available_regular_slots = db.query(SurveySlot).filter(
                    SurveySlot.is_gold == 0
                ).all()
                
                if available_regular_slots:
                    # Randomly select from available regular slots (both usage_count = 0 and 1)
                    assigned_slot = random.choice(available_regular_slots)

            # # C. Fallback: If ALL slots are full (e.g., user #55), randomly pick from least used ones
            # if not assigned_slot:
            #     # Get all slots ordered by usage_count
            #     all_slots = db.query(SurveySlot).order_by(SurveySlot.usage_count).all()
            #     if all_slots:
            #         # Find the minimum usage_count
            #         min_usage = all_slots[0].usage_count
            #         # Get all slots with minimum usage_count
            #         least_used_slots = [slot for slot in all_slots if slot.usage_count == min_usage]
            #         # Randomly select from least used slots
            #         assigned_slot = random.choice(least_used_slots)

            if not assigned_slot:
                flash("Error: No survey slots available.", "danger")
                return redirect(url_for("home"))

            # D. Increment Usage
            assigned_slot.usage_count += 1
            db.commit()

            # E. PRE-FILL DRAFTS (The "Reservation")
            # We decode the list of 20 IDs: [102, 55, 3...]
            poem_ids = json.loads(assigned_slot.poem_ids_json)

            for p_id in poem_ids:
                new_draft = ResponseDraft(
                    poem_id=p_id,
                    email=email,
                    # All other fields (clarity, etc.) remain NULL
                )
                db.add(new_draft)
            
            db.commit()
            
            # Start at Question 1
            return redirect(url_for("survey_route", page_num=1))

    finally:
        db.close()

@app.route("/survey/<int:page_num>", methods=["GET", "POST"])
def survey_route(page_num):
    # This route now uses PAGE NUMBER (1-20), not Poem ID.
    
    if "user_email" not in session:
        return redirect(url_for("home"))
    
    email = session["user_email"]
    db = next(get_db())

    try:
        # 1. Get all drafts for this user (Sequence 1-20)
        drafts = db.query(ResponseDraft).filter_by(email=email).order_by(ResponseDraft.draft_id).all()

        if not drafts:
            # If drafts are missing but the user already submitted, go to Thank You.
            response_count = db.query(func.count(Response.user_id)).filter_by(email=email).scalar() or 0
            if response_count >= TOTAL_POEMS:
                return redirect(url_for("thank_you"))
            return redirect(url_for("survey_start"))

        if page_num < 1 or page_num > len(drafts):
            return redirect(url_for("survey_start"))

        # 2. Identify the specific draft for this page
        # List index is page_num - 1
        current_draft = drafts[page_num - 1]
        
        # 3. Fetch the actual Poem content
        poem = db.query(Poem).get(current_draft.poem_id)

        # 4. HANDLE SAVE (POST)
        if request.method == "POST":
            current_draft.clarity = request.form.get("clarity")
            current_draft.devices = request.form.get("devices")
            current_draft.punctuation = request.form.get("punctuation")
            current_draft.grammar = request.form.get("grammar")
            current_draft.originality = request.form.get("originality")
            current_draft.extra = request.form.get("extra")
            
            db.commit()

            # Navigation
            if page_num < TOTAL_POEMS:
                return redirect(url_for("survey_route", page_num=page_num + 1))
            else:
                # FINAL SUBMISSION LOGIC
                # Copy Drafts -> Final Responses
                for d in drafts:
                    # Check duplication
                    exists = db.query(Response).filter_by(email=email, poem_id=d.poem_id).first()
                    if not exists:
                        final = Response(
                            poem_id=d.poem_id, email=d.email,
                            clarity=d.clarity, devices=d.devices, 
                            punctuation=d.punctuation, grammar=d.grammar, 
                            originality=d.originality, extra=d.extra
                        )
                        db.add(final)
                db.commit()

                # After successful submission, drafts are no longer needed.
                db.query(ResponseDraft).filter_by(email=email).delete(synchronize_session=False)
                db.commit()
                return redirect(url_for("thank_you"))

        # 5. RENDER
        return render_template(
            "survey.html",
            poem=poem,
            draft=current_draft,
            current_index=page_num,  # Pass the Page Number (1-20)
            total_poems=TOTAL_POEMS
        )

    finally:
        db.close()

@app.route("/thank-you")
def thank_you():
    return render_template("thank_you.html")

if __name__ == "__main__":
    app.run(debug=True, port=8000)