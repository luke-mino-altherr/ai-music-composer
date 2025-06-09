import logging
from typing import List, Tuple, Dict
from neomodel import config, db
from music21 import (
    note, pitch, interval, scale, chord,
    key, roman
)
from .models import (
    Interval, Tone, Scale, Chord, ChordInstance, ScaleInstance,
    TONICS, get_alternative_name
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define common intervals, scales, and chord types
INTERVALS = [
    'P1',  # Perfect unison
    'A1',  # Augmented unison
    'm2', 'M2',  # Minor and major seconds
    'm3', 'M3',  # Minor and major thirds
    'P4', 'A4',  # Perfect and augmented fourth
    'd5', 'P5', 'A5',  # Diminished, perfect, and augmented fifths
    'm6', 'M6',  # Minor and major sixths
    'd7', 'm7', 'M7',  # Diminished, minor, and major sevenths
    'P8',  # Perfect octave
    'd2', 'A2',  # Additional intervals that might occur
    'd3', 'A3',
    'd4',
    'd6', 'A6',
    'A7'
]
SCALE_TYPES = ['major', 'minor', 'harmonicMinor', 'melodicMinor', 'dorian', 'phrygian', 'lydian', 'mixolydian', 'locrian']
CHORD_TYPES = ['major', 'minor', 'diminished', 'augmented', 'dominant-seventh', 'major-seventh', 'minor-seventh', 'half-diminished-seventh', 'diminished-seventh']

def get_note_chroma(note_name: str) -> int:
    """Get the pitch class (chroma) of a note"""
    return pitch.Pitch(note_name).pitchClass

def get_scale_notes(tonic: str, scale_type: str) -> List[str]:
    """Get all notes in a scale"""
    if scale_type == 'major':
        sc = scale.MajorScale(tonic)
    elif scale_type == 'minor':
        sc = scale.MinorScale(tonic)
    elif scale_type == 'harmonicMinor':
        sc = scale.HarmonicMinorScale(tonic)
    elif scale_type == 'melodicMinor':
        sc = scale.MelodicMinorScale(tonic)
    elif scale_type == 'dorian':
        sc = scale.DorianScale(tonic)
    elif scale_type == 'phrygian':
        sc = scale.PhrygianScale(tonic)
    elif scale_type == 'lydian':
        sc = scale.LydianScale(tonic)
    elif scale_type == 'mixolydian':
        sc = scale.MixolydianScale(tonic)
    elif scale_type == 'locrian':
        sc = scale.LocrianScale(tonic)
    else:
        raise ValueError(f"Unsupported scale type: {scale_type}")
    
    return [normalize_note_name(p.name) for p in sc.getPitches()]

def normalize_note_name(note_name: str) -> str:
    """Convert complex note names (double sharps/flats) to simpler enharmonic equivalents"""
    # Use music21's pitch object to normalize the note name
    p = pitch.Pitch(note_name)
    # Get the pitch class number (0-11)
    pc = p.pitchClass
    # Find the simplest note name for this pitch class from our TONICS list
    for note in TONICS:
        if pitch.Pitch(note).pitchClass == pc:
            return note
    # If no match found (shouldn't happen), return original
    return note_name

def get_chord_notes(tonic: str, chord_type: str) -> List[str]:
    """Get all notes in a chord"""
    if chord_type == 'major':
        ch = chord.Chord([tonic, interval.Interval('M3').transposePitch(pitch.Pitch(tonic)), 
                         interval.Interval('P5').transposePitch(pitch.Pitch(tonic))])
    elif chord_type == 'minor':
        ch = chord.Chord([tonic, interval.Interval('m3').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('P5').transposePitch(pitch.Pitch(tonic))])
    elif chord_type == 'diminished':
        ch = chord.Chord([tonic, interval.Interval('m3').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('d5').transposePitch(pitch.Pitch(tonic))])
    elif chord_type == 'augmented':
        ch = chord.Chord([tonic, interval.Interval('M3').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('A5').transposePitch(pitch.Pitch(tonic))])
    elif chord_type == 'dominant-seventh':
        ch = chord.Chord([tonic, interval.Interval('M3').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('P5').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('m7').transposePitch(pitch.Pitch(tonic))])
    elif chord_type == 'major-seventh':
        ch = chord.Chord([tonic, interval.Interval('M3').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('P5').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('M7').transposePitch(pitch.Pitch(tonic))])
    elif chord_type == 'minor-seventh':
        ch = chord.Chord([tonic, interval.Interval('m3').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('P5').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('m7').transposePitch(pitch.Pitch(tonic))])
    elif chord_type == 'half-diminished-seventh':
        ch = chord.Chord([tonic, interval.Interval('m3').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('d5').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('m7').transposePitch(pitch.Pitch(tonic))])
    elif chord_type == 'diminished-seventh':
        ch = chord.Chord([tonic, interval.Interval('m3').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('d5').transposePitch(pitch.Pitch(tonic)),
                         interval.Interval('d7').transposePitch(pitch.Pitch(tonic))])
    else:
        raise ValueError(f"Unsupported chord type: {chord_type}")
    
    return [normalize_note_name(p.name) for p in ch.pitches]

def get_chord_intervals(chord_type: str) -> List[str]:
    """Get the intervals in a chord type"""
    if chord_type == 'major':
        return ['P1', 'M3', 'P5']
    elif chord_type == 'minor':
        return ['P1', 'm3', 'P5']
    elif chord_type == 'diminished':
        return ['P1', 'm3', 'd5']
    elif chord_type == 'augmented':
        return ['P1', 'M3', 'A5']
    elif chord_type == 'dominant-seventh':
        return ['P1', 'M3', 'P5', 'm7']
    elif chord_type == 'major-seventh':
        return ['P1', 'M3', 'P5', 'M7']
    elif chord_type == 'minor-seventh':
        return ['P1', 'm3', 'P5', 'm7']
    elif chord_type == 'half-diminished-seventh':
        return ['P1', 'm3', 'd5', 'm7']
    elif chord_type == 'diminished-seventh':
        return ['P1', 'm3', 'd5', 'd7']
    return ['P1']  # Default for unknown chord types

def clear_database():
    """Clear all nodes and relationships from the database"""
    db.cypher_query("MATCH (n) DETACH DELETE n")
    logger.info("Database cleared")

def init_indexes():
    """Create indexes for all node labels"""
    indexes = [
        'Interval',
        'Tone',
        'Scale',
        'Chord',
        'ChordInstance',
        'ScaleInstance'
    ]
    for label in indexes:
        try:
            db.cypher_query(f"CREATE INDEX ON :{label}(name)")
        except:
            # Index might already exist
            pass
    logger.info("Indexes created successfully")

def init_intervals():
    """Initialize musical intervals"""
    for interval_name in INTERVALS:
        Interval(name=interval_name).save()
    logger.info("Intervals initialized")

def init_notes():
    """Initialize musical notes/tones"""
    for note_name in TONICS:
        Tone(
            name=note_name,
            chroma=get_note_chroma(note_name),
            alternative_name=get_alternative_name(note_name)
        ).save()
    logger.info("Notes initialized")

def init_scales():
    """Initialize scale types"""
    for scale_name in SCALE_TYPES:
        Scale(name=scale_name).save()
    logger.info("Scales initialized")

def init_chords():
    """Initialize chord types"""
    for chord_name in CHORD_TYPES:
        Chord(name=chord_name).save()
    logger.info("Chords initialized")

def connect_chord_intervals(chord_intervals: Dict[str, List[str]]):
    """Connect chords to their intervals"""
    for chord_name, intervals in chord_intervals.items():
        chord = Chord.nodes.get(name=chord_name)
        for interval_name in intervals:
            interval_node = Interval.nodes.get(name=interval_name)
            chord.contains.connect(interval_node)
    logger.info("Chord intervals connected")

def generate_note_distances():
    """Create interval relationships between all notes"""
    notes = Tone.nodes.all()
    for note1 in notes:
        for note2 in notes:
            # Create interval between notes
            i = interval.Interval(noteStart=pitch.Pitch(note1.name), 
                                noteEnd=pitch.Pitch(note2.name))
            note1.intervals.connect(note2, {'distance': i.name})
    logger.info("Note distances generated")

def init_chord_instances():
    """Initialize chord instances with their notes and intervals"""
    for chord_type in CHORD_TYPES:
        chord_node = Chord.nodes.get(name=chord_type)
        intervals = get_chord_intervals(chord_type)
        
        for tonic in TONICS:
            instance_name = f"{tonic} {chord_type}"
            notes = get_chord_notes(tonic, chord_type)
            
            # Create chord instance
            chord_instance = ChordInstance(name=instance_name).save()
            chord_instance.instance_of.connect(chord_node)
            
            # Connect tonic
            tonic_note = Tone.nodes.get(name=tonic)
            chord_instance.has_tonic.connect(tonic_note)
            
            # Connect notes and intervals
            for note_name, interval_name in zip(notes, intervals):
                note_node = Tone.nodes.get(name=note_name)
                interval_node = Interval.nodes.get(name=interval_name)
                
                # Connect note to chord instance
                note_node.in_chords.connect(chord_instance, {'function': interval_name})
                
                # Connect interval to chord instance
                chord_instance.contains.connect(interval_node, {'instance': note_name})
    
    logger.info("Chord instances initialized")

def init_scale_instances():
    """Initialize scale instances with their notes"""
    for scale_type in SCALE_TYPES:
        scale_node = Scale.nodes.get(name=scale_type)
        
        for tonic in TONICS:
            instance_name = f"{tonic} {scale_type}"
            notes = get_scale_notes(tonic, scale_type)
            
            # Create scale instance
            scale_instance = ScaleInstance(name=instance_name).save()
            scale_instance.instance_of.connect(scale_node)
            
            # Connect notes to scale instance
            for note_name in notes:
                note_node = Tone.nodes.get(name=note_name)
                note_node.in_scales.connect(scale_instance)
            
            # Connect intervals to scale
            prev_note = None
            for note_name in notes:
                if prev_note:
                    i = interval.Interval(noteStart=pitch.Pitch(prev_note),
                                        noteEnd=pitch.Pitch(note_name))
                    interval_node = Interval.nodes.get(name=i.name)
                    scale_node.contains.connect(interval_node)
                prev_note = note_name
    
    logger.info("Scale instances initialized")

def initialize_music_database(uri: str = "bolt://localhost:7687",
                            username: str = "neo4j",
                            password: str = "musiccomposer",
                            clear: bool = False):
    """Initialize the complete music theory database"""
    # Configure the database connection
    config.DATABASE_URL = f"bolt://{username}:{password}@{uri.split('://')[1]}"
    
    try:
        if clear:
            clear_database()
        
        # Initialize basic music theory components
        init_indexes()
        init_intervals()
        init_notes()
        init_scales()
        init_chords()
        
        # Generate relationships
        connect_chord_intervals({
            chord_type: get_chord_intervals(chord_type)
            for chord_type in CHORD_TYPES
        })
        
        generate_note_distances()
        
        # Initialize instances
        init_chord_instances()
        init_scale_instances()
        
        logger.info("Music database initialization completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize music database: {str(e)}")
        return False

if __name__ == "__main__":
    initialize_music_database(clear=True) 