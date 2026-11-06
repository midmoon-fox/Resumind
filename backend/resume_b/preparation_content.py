"""Pure preparation validation; services always supply the source document for ownership checks."""
from .documents import fields, require, string, uuid4 as validate_uuid


def validate_content(content, kind, document=None):
    fields(content, "introduction questions", "/content")
    require(isinstance(content["questions"], list), "/content/questions", "expected array")
    if kind == "INTRODUCTION":
        string(content["introduction"], "/content/introduction")
        require(bool(content["introduction"].strip()) and not content["questions"], "/content", "introduction requires text and no questions")
        return
    require(kind == "INTERVIEW_QUESTIONS", "/type", "unsupported preparation type")
    require(content["introduction"] is None and 5 <= len(content["questions"]) <= 10, "/content", "question set requires null introduction and 5..10 questions")
    basis_ids = {item["id"] for section in document["sections"] for item in section["items"]} if document is not None else set()
    seen = set()
    for i, question in enumerate(content["questions"]):
        path = f"/content/questions/{i}"
        fields(question, "id number question referenceAnswer basisItemIds missingFacts", path)
        validate_uuid(question["id"], path + "/id")
        require(question["id"] not in seen, path + "/id", "duplicate question ID")
        seen.add(question["id"])
        require(type(question["number"]) is int and question["number"] == i + 1, path + "/number", "question numbers must be contiguous from 1")
        for key in ("question", "referenceAnswer"):
            string(question[key], path + "/" + key)
        require(bool(question["question"].strip()), path + "/question", "question cannot be empty")
        require(isinstance(question["basisItemIds"], list), path + "/basisItemIds", "expected array")
        for identifier in question["basisItemIds"]:
            validate_uuid(identifier, path + "/basisItemIds")
            require(document is None or identifier in basis_ids, path + "/basisItemIds", "basis must belong to fixed resume version")
        require(isinstance(question["missingFacts"], list), path + "/missingFacts", "expected array")
        for fact in question["missingFacts"]:
            string(fact, path + "/missingFacts")

