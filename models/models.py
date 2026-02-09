from sqlalchemy import Column, Integer, String, Text, Enum, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.mysql import LONGTEXT, TINYINT
from sqlalchemy.orm import relationship
from db import Base

# Define the Likert scale options
LIKERT_SCALE = ('Very Unlikely', 'Unlikely', 'Not Sure', 'Likely', 'Very Likely')

class Poem(Base):
    __tablename__ = "poems"

    # Schema from poems.png
    poem_id = Column(Integer, primary_key=True, autoincrement=True)
    
    # MAPPING: We map 'content' to your actual column 'generated_poem'
    content = Column("generated_poem", LONGTEXT)
    
    # COLUMNS FROM SCHEMA (mapped but not necessarily used in UI)
    topic = Column(LONGTEXT) # You mentioned ignoring this
    model = Column(LONGTEXT)
    prompt_type = Column(LONGTEXT)
    themes = Column(LONGTEXT)
    flag = Column(TINYINT)
    source_type = Column(LONGTEXT)

    # SMART TITLE: Since we don't have a title column, we generate one automatically.
    # This allows {{ poem.title }} to work in your HTML without errors.
    @property
    def title(self):
        return f"Poem #{self.poem_id}"

    # Relationships
    responses = relationship("Response", back_populates="poem")
    drafts = relationship("ResponseDraft", back_populates="poem")

class Response(Base):
    __tablename__ = "responses"

    # Schema from responses.png: PK is 'user_id'
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    
    poem_id = Column(Integer, ForeignKey("poems.poem_id"), nullable=False)
    email = Column(String(255), nullable=False)
    
    clarity = Column(Enum(*LIKERT_SCALE), nullable=True)
    devices = Column(Enum(*LIKERT_SCALE), nullable=True)
    punctuation = Column(Enum(*LIKERT_SCALE), nullable=True)
    grammar = Column(Enum(*LIKERT_SCALE), nullable=True)
    originality = Column(Enum(*LIKERT_SCALE), nullable=True)
    extra = Column(Text, nullable=True)

    poem = relationship("Poem", back_populates="responses")

class ResponseDraft(Base):
    __tablename__ = "responses_drafts"

    # Schema from responses_drafts.png: PK is 'draft_id'
    draft_id = Column(Integer, primary_key=True, autoincrement=True)
    
    poem_id = Column(Integer, ForeignKey("poems.poem_id"), nullable=False)
    email = Column(String(255), nullable=False)
    
    clarity = Column(Enum(*LIKERT_SCALE), nullable=True)
    devices = Column(Enum(*LIKERT_SCALE), nullable=True)
    punctuation = Column(Enum(*LIKERT_SCALE), nullable=True)
    grammar = Column(Enum(*LIKERT_SCALE), nullable=True)
    originality = Column(Enum(*LIKERT_SCALE), nullable=True)
    extra = Column(Text, nullable=True)
    
    last_updated = Column(TIMESTAMP, server_default=func.now(), onupdate=func.current_timestamp())

    poem = relationship("Poem", back_populates="drafts")


class SurveySlot(Base):
    __tablename__ = "survey_slots"

    slot_id = Column(Integer, primary_key=True)
    poem_ids_json = Column(Text, nullable=False) # Stores "[102, 55, 3...]"
    is_gold = Column(TINYINT, default=0)         # 1 = Gold, 0 = Regular
    usage_count = Column(Integer, default=0)