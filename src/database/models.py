from neomodel import (
    StructuredNode,
    StringProperty,
    IntegerProperty,
    FloatProperty,
    RelationshipTo,
    RelationshipFrom,
    One,
    ZeroOrMore,
    StructuredRel,
    config
)

# Configure neomodel to connect to Neo4j
config.DATABASE_URL = 'bolt://neo4j:musiccomposer@localhost:7687'

class InRel(StructuredRel):
    """Relationship for notes in a chord/scale with their function"""
    function = StringProperty()  # For storing interval function in the chord/scale

class IntervalRel(StructuredRel):
    """Relationship between notes with their interval distance"""
    distance = StringProperty()  # e.g. "M3" for major third

class ContainsRel(StructuredRel):
    """Relationship for intervals in chords/scales with optional instance note"""
    instance = StringProperty(required=False)  # For storing the actual note in an instance

class Interval(StructuredNode):
    """Represents a musical interval (e.g. M3, P5)"""
    name = StringProperty(unique_index=True, required=True)  # e.g. "M3" for major third

class Tone(StructuredNode):
    """Represents a musical note/tone"""
    name = StringProperty(unique_index=True, required=True)  # e.g. "C", "F#"
    chroma = IntegerProperty(required=True)  # Integer 0-11 representing pitch class
    alternative_name = StringProperty(default="")  # e.g. "Db" for "C#"
    
    # Relationships
    intervals = RelationshipTo('Tone', 'INTERVAL', model=IntervalRel)
    in_chords = RelationshipTo('ChordInstance', 'IN', model=InRel)
    in_scales = RelationshipTo('ScaleInstance', 'IN')

class Scale(StructuredNode):
    """Represents a scale type (e.g. major, minor)"""
    name = StringProperty(unique_index=True, required=True)
    
    # Relationships
    contains = RelationshipTo('Interval', 'CONTAINS')
    instances = RelationshipFrom('ScaleInstance', 'INSTANCE_OF')

class Chord(StructuredNode):
    """Represents a chord type (e.g. maj7, min7)"""
    name = StringProperty(unique_index=True, required=True)
    
    # Relationships
    contains = RelationshipTo('Interval', 'CONTAINS')
    instances = RelationshipFrom('ChordInstance', 'INSTANCE_OF')

class ChordInstance(StructuredNode):
    """Represents a specific chord with a root (e.g. Cmaj7)"""
    name = StringProperty(unique_index=True, required=True)
    
    # Relationships
    instance_of = RelationshipTo('Chord', 'INSTANCE_OF', cardinality=One)
    has_tonic = RelationshipTo('Tone', 'HAS_TONIC', cardinality=One)
    contains = RelationshipTo('Interval', 'CONTAINS', model=ContainsRel)
    notes = RelationshipFrom('Tone', 'IN', model=InRel)

class ScaleInstance(StructuredNode):
    """Represents a specific scale with a root (e.g. C major)"""
    name = StringProperty(unique_index=True, required=True)
    
    # Relationships
    instance_of = RelationshipTo('Scale', 'INSTANCE_OF', cardinality=One)
    notes = RelationshipFrom('Tone', 'IN')

# Constants for music theory
TONICS = [
    'A', 'A#', 'Bb', 'B', 'C', 'C#', 'Db',
    'D', 'D#', 'Eb', 'E', 'F', 'F#', 'Gb',
    'G', 'G#', 'Ab'
]

TWO_WAY_ALTERNATIVE_NAMES = {
    'C#': 'Db', 'Db': 'C#',
    'D#': 'Eb', 'Eb': 'D#',
    'F#': 'Gb', 'Gb': 'F#',
    'G#': 'Ab', 'Ab': 'G#',
    'A#': 'Bb', 'Bb': 'A#'
}

def get_alternative_name(note: str) -> str:
    """Get the enharmonic equivalent name for a note"""
    return TWO_WAY_ALTERNATIVE_NAMES.get(note, "")

class Note(StructuredNode):
    """
    Represents a musical note in the composition
    """
    identifier = StringProperty(unique_index=True, required=True)
    pitch = IntegerProperty(required=True)  # MIDI pitch number
    duration = FloatProperty(required=True)  # Duration in beats
    velocity = IntegerProperty(required=True)  # MIDI velocity (0-127)
    position = FloatProperty(required=True)  # Position in beats from start
    
    # Relationships
    piece = RelationshipTo('Piece', 'PART_OF', cardinality=One)
    next_note = RelationshipTo('Note', 'NEXT', cardinality=ZeroOrMore)
    previous_note = RelationshipFrom('Note', 'NEXT', cardinality=ZeroOrMore)

    def to_dict(self):
        return {
            'identifier': self.identifier,
            'pitch': self.pitch,
            'duration': self.duration,
            'velocity': self.velocity,
            'position': self.position
        }

class Piece(StructuredNode):
    """
    Represents a complete musical piece
    """
    identifier = StringProperty(unique_index=True, required=True)
    name = StringProperty(required=True)
    tempo = IntegerProperty(required=True)
    key = StringProperty(required=True)
    time_signature = StringProperty(default='4/4')
    
    # Relationships
    notes = RelationshipFrom('Note', 'PART_OF', cardinality=ZeroOrMore)

    def to_dict(self):
        return {
            'identifier': self.identifier,
            'name': self.name,
            'tempo': self.tempo,
            'key': self.key,
            'time_signature': self.time_signature
        }

    def get_notes_ordered(self):
        """
        Retrieve all notes in this piece ordered by position
        """
        return self.notes.order_by('position') 