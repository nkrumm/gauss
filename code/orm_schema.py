from mongokit import Document, ValidationError, OR
from bson.objectid import ObjectId
import datetime


def sample_id_validator(value):
    if not bool(len(value) > 3):
        raise ValidationError(
            '%s is too short! Minimum sample_id length is 3.')
    else:
        return True


class Sample(Document):
    """
    MongoKit document class for sample
    """
    use_dot_notation = True
    dot_notation_warning = True

    structure = {
        #'_id': ObjectId,
        "identifier": {
            "sample_id": basestring,
            "study_id": ObjectId,
            "study_name": basestring,
            "date_added": datetime.datetime
        },
        "relationships": [{
            "type": basestring,
            "id": int,
            "date_added": datetime.datetime
        }],
        "files": [{
            "filename": basestring,
            "filetype": basestring,
            "metadata": dict,
            "date_imported": datetime.datetime
        }],
        "attributes": [{
            "name": basestring,
            "description": basestring,
            "value_type": basestring,
            "value": None,
            "date_added": datetime.datetime
        }]
    }

    validators = {
        "identifier.sample_id": sample_id_validator
    }

    default_values = {"identifier.date_added": datetime.datetime.utcnow}

    required_fields = ['identifier.sample_id',
                       'identifier.study_id']

    indexes = [
        {
            "fields": ['identifier.sample_id', 'identifier.study_id'],
            "unique": True,
        },
        {
            "fields": ['identifier.study_name'],
            "unique": False,
        }
    ]

    pass


class Study(Document):
    """
    MongoKit document type for study, which houses samples
    """
    use_dot_notation = True
    dot_notation_warning = True

    structure = {
        "study_name": basestring,
        "study_description": basestring,
        "date_added": datetime.datetime
    }

    default_values = {"date_added": datetime.datetime.utcnow}

    required_fields = ['study_name']

    pass

class Variant(Document):
    """
    MongoAlchemy ORM for variant Document
    """
    use_dot_notation = True
    dot_notation_warning = True

    structure = {
        "sample_id": ObjectId,
        "sample_name": basestring,
        "chrom": basestring,
        "start": int,
        "stop": int,
        "id": basestring,
        "ref": basestring,
        "alt": basestring,
        "qual": float,
        "filter": [basestring],
        "data": basestring,
        "annotations": dict
    }

    required_fields = ['sample_id','chrom','start','filter']

    pass


class Variant_annotation(Document):
    """
    ORM for variant_annotation Document
    """
    pass


class Annotation(Document):
    """
    ORM for annotation Document
    """
    pass

class Filter(Document):
    """
    ORM for filter set document
    """
    pass
