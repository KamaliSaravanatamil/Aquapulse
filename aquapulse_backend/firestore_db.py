"""Small storage adapter backed by Google Cloud Firestore."""

import json
import os
import uuid
from copy import deepcopy
from typing import Any, Dict, Iterable, Optional

import firebase_admin
from firebase_admin import credentials, firestore


class DuplicateKeyError(Exception):
    """Raised when a Firestore document ID is already in use."""


class FirestoreCursor:
    def __init__(self, documents: Iterable[Dict[str, Any]]):
        self._documents = list(documents)

    def sort(self, field: str, direction: int = 1):
        self._documents.sort(
            key=lambda document: (
                document.get(field) is not None,
                document.get(field),
            ),
            reverse=direction < 0,
        )
        return self

    def skip(self, count: int):
        self._documents = self._documents[count:]
        return self

    def limit(self, count: int):
        self._documents = self._documents[:count]
        return self

    def __iter__(self):
        return iter(self._documents)


def _matches(document: Dict[str, Any], query: Dict[str, Any]) -> bool:
    for field, expected in query.items():
        actual = document.get(field)
        if isinstance(expected, dict):
            for operator, value in expected.items():
                if operator == "$gte" and not (actual is not None and actual >= value):
                    return False
                if operator == "$lte" and not (actual is not None and actual <= value):
                    return False
                if operator == "$gt" and not (actual is not None and actual > value):
                    return False
                if operator == "$lt" and not (actual is not None and actual < value):
                    return False
        elif actual != expected:
            return False
    return True


class FirestoreCollection:
    def __init__(self, client, collection):
        self._client = client
        self._collection = collection

    def _documents(self):
        for snapshot in self._collection.stream():
            document = snapshot.to_dict() or {}
            document["_id"] = snapshot.id
            yield document

    def find(self, query: Optional[Dict[str, Any]] = None):
        query = query or {}
        return FirestoreCursor(
            deepcopy(document)
            for document in self._documents()
            if _matches(document, query)
        )

    def find_one(self, query: Optional[Dict[str, Any]] = None, sort=None):
        cursor = self.find(query)
        if sort:
            for field, direction in reversed(sort):
                cursor.sort(field, direction)
        return next(iter(cursor), None)

    def insert_one(self, document: Dict[str, Any]):
        data = deepcopy(document)
        document_id = str(
            data.get("device_id")
            if self._collection.id == "devices" and data.get("device_id")
            else uuid.uuid4()
        )
        if self._collection.document(document_id).get().exists:
            raise DuplicateKeyError(f"Document already exists: {document_id}")
        data.pop("_id", None)
        self._collection.document(document_id).set(data)
        return type("InsertOneResult", (), {"inserted_id": document_id})()

    def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        document = self.find_one(query)
        if not document:
            return type("UpdateResult", (), {"matched_count": 0})()
        document_id = document.pop("_id")
        data = deepcopy(document)
        data.update(update.get("$set", {}))
        self._collection.document(document_id).set(data)
        return type("UpdateResult", (), {"matched_count": 1})()

    def delete_many(self, query: Optional[Dict[str, Any]] = None):
        documents = list(self.find(query))
        batch = self._client.batch()
        for document in documents:
            batch.delete(self._collection.document(document["_id"]))
        if documents:
            batch.commit()
        return type("DeleteResult", (), {"deleted_count": len(documents)})()

    def count_documents(self, query: Optional[Dict[str, Any]] = None):
        return sum(1 for _ in self.find(query))


class FirestoreDatabase:
    def __init__(self, client):
        self._client = client

    def __getitem__(self, collection_name: str):
        return FirestoreCollection(
            self._client,
            self._client.collection(collection_name),
        )

    def __getattr__(self, collection_name: str):
        if collection_name.startswith("_"):
            raise AttributeError(collection_name)
        return self[collection_name]


def create_firestore_database() -> FirestoreDatabase:
    """Create a Firestore client from configured or application-default credentials."""
    if not firebase_admin._apps:
        service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
        if service_account_json:
            credential = credentials.Certificate(json.loads(service_account_json))
        else:
            credential_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            credential = (
                credentials.Certificate(credential_path)
                if credential_path
                else credentials.ApplicationDefault()
            )
        firebase_admin.initialize_app(
            credential,
            {
                "projectId": os.getenv("FIREBASE_PROJECT_ID", "aquapulse-2752b"),
            },
        )
    return FirestoreDatabase(firestore.client())
