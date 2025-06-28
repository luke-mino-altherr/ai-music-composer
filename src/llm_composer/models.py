"""Pydantic models for MIDI commands."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, confloat, conint


class NoteData(BaseModel):
    """Data for a single note in a sequence."""

    pitch: conint(ge=0, le=127) = Field(..., description="MIDI note number (0-127)")
    velocity: conint(ge=0, le=127) = Field(
        default=100, description="Note velocity (0-127)"
    )
    duration: confloat(gt=0) = Field(default=0.5, description="Note duration in beats")
    channel: conint(ge=0, le=15) = Field(default=0, description="MIDI channel (0-15)")


class PlayNoteCommand(BaseModel):
    """Command to play a single note."""

    type: Literal["play_note"]
    instrument: str = Field(..., description="Name of the instrument to play")
    note: conint(ge=0, le=127) = Field(..., description="MIDI note number (0-127)")
    velocity: Optional[conint(ge=0, le=127)] = Field(
        None, description="Note velocity (0-127)"
    )
    duration: confloat(gt=0) = Field(default=0.5, description="Note duration in beats")


class PlaySequenceCommand(BaseModel):
    """Command to play a sequence of notes."""

    type: Literal["play_sequence"]
    notes: List[NoteData] = Field(..., description="List of notes in the sequence")
    instrument: Optional[str] = Field(
        None, description="Name of the instrument to play"
    )
    loop: bool = Field(default=False, description="Whether to loop the sequence")


class CreateInstrumentCommand(BaseModel):
    """Command to create a new instrument."""

    type: Literal["create_instrument"]
    name: str = Field(..., description="Name of the instrument")
    channel: conint(ge=0, le=15) = Field(..., description="MIDI channel (0-15)")
    velocity: conint(ge=0, le=127) = Field(
        default=100, description="Default velocity (0-127)"
    )
    transpose: conint(ge=-127, le=127) = Field(
        default=0, description="Transposition in semitones"
    )


class RemoveInstrumentCommand(BaseModel):
    """Command to remove an instrument."""

    type: Literal["remove_instrument"]
    name: str = Field(..., description="Name of the instrument to remove")


class StopSequenceCommand(BaseModel):
    """Command to stop a sequence."""

    type: Literal["stop_sequence"]
    sequence_id: int = Field(..., description="ID of the sequence to stop")


class StopAllCommand(BaseModel):
    """Command to stop all sequences and instruments."""

    type: Literal["stop_all"]


# Union of all possible commands
MIDICommand = (
    PlayNoteCommand
    | PlaySequenceCommand
    | CreateInstrumentCommand
    | RemoveInstrumentCommand
    | StopSequenceCommand
    | StopAllCommand
)
