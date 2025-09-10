import {createRoot} from "react-dom/client";
import React, {useEffect, useState} from "react";
import {
    CCard,
    CCardBody,
    CCardHeader,
    CTable,
    CTableBody,
    CTableDataCell,
    CTableHead,
    CTableHeaderCell,
    CTableRow,
    CNav,
    CNavItem,
    CNavLink,
    CTabContent,
    CTabPane,
} from "@coreui/react";

const container = document.getElementById("root_container");
const root = createRoot(container);
const model_data = document.getElementById("model").innerText;
const model = JSON.parse(model_data);
const csrf_token = document.getElementById("csrf_token").innerText.trim();

function App({model, csrf_token}) {
    return <CollectionInfoPage data={model}/>;
}

const dataTypeMap = {
    5: "Int64",
    21: "VarChar",
    101: "FloatVector",
};

function CollectionInfoPage({data}) {
    const [activeTab, setActiveTab] = useState("documents")

    const {collection_id, collection_name, description, num_entities, fields, indexes, status, documents = []} = data

    const [documentsList, setDocumentsList] = useState(documents)
    const [selectedDocId, setSelectedDocId] = useState("")

    const [availableDocuments, setAvailableDocuments] = useState([])
    const [refreshFlag, setRefreshFlag] = useState(0)

    const [isIndexing, setIsIndexing] = useState(status === "running")
    const [isFlushing, setIsFlushing] = useState(false)


    useEffect(() => {
        fetch("/management/ViewModelCollection/all_documents", {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrf_token,
            },
        })
            .then((res) => {
                if (!res.ok) throw new Error("Failed to load documents");
                return res.json();
            })
            .then((data) => {
                setAvailableDocuments(data);
            })
            .catch((err) => {
                console.error("Error loading documents:", err);
            })
    }, [])

    useEffect(() => {
        fetch("/management/ViewModelCollection/get_documents_by_collection_id?collection_id=" + collection_id, {
            method: "GET",
            headers: {
                "X-CSRFToken": csrf_token,
            }
        })
            .then((res) => {
                if (!res.ok) throw new Error("Failed to load collection documents");
                return res.json();
            })
            .then((data) => {
                setDocumentsList(data)
            })
            .catch((err) => {
                console.error("Error loading collection documents:", err)
            })
    }, [collection_id, refreshFlag])


    function handleAddDocument() {
        const formData = new FormData()
        formData.append("collection_id", collection_id)
        formData.append("document_id", selectedDocId)

        fetch("/management/ViewModelCollection/add_document_to_collection", {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrf_token,
            },
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.status === "success") {
                    setRefreshFlag((prev) => prev + 1)
                } else {
                    alert("Failed: " + data.message);
                }
            })
            .catch((err) => {
                alert("Error: " + err);
            })
    }


    function handleRemoveDocument(docId) {
        const formData = new FormData()
        formData.append("collection_id", collection_id)
        formData.append("document_id", docId)

        fetch("/management/ViewModelCollection/remove_document_from_collection", {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrf_token,
            },
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.status === "success") {
                    setDocumentsList(documentsList.filter((doc) => doc.id !== docId))
                } else {
                    alert("Failed: " + data.message);
                }
            })
            .catch((err) => {
                alert("Error: " + err);
            })
    }

    function handleFlushCollection() {
        setIsFlushing(true)
        fetch("/management/ViewModelCollection/flush_collection?collection_id=" + collection_id, {
            method: "GET",
            headers: {
                "X-CSRFToken": csrf_token,
            }
        })
            .then((res) => {
                if (!res.ok) throw new Error("Failed to flush collection")
                setIsFlushing(false)
            })
            .catch((err) => {
                console.error("Error flush collection:", err)
            })
    }

    function handleIndexCollection() {
        const formData = new FormData()
        formData.append("collection_id", collection_id)

        fetch("/management/ViewModelCollection/index_collection", {
            method: "POST",
            body: formData,
            headers: {
                "X-CSRFToken": csrf_token,
            },
        })
            .then((res) => res.json())
            .then((data) => {
                if (data.status === "success") {
                    setIsIndexing(true)
                } else {
                    alert("Failed: " + data.message);
                }
            })
            .catch((err) => {
                alert("Error: " + err);
            })
    }

    return (
        <>
            <h5>Collection: {collection_name}</h5>

            <CNav variant="tabs" role="tablist" className="mb-3">
                <CNavItem>
                    <CNavLink active={activeTab === "documents"} onClick={() => setActiveTab("documents")}>
                        Documents
                    </CNavLink>
                </CNavItem>
                <CNavItem>
                    <CNavLink active={activeTab === "overview"} onClick={() => setActiveTab("overview")}>
                        Overview
                    </CNavLink>
                </CNavItem>
                <CNavItem>
                    <CNavLink active={activeTab === "tasks"} onClick={() => setActiveTab("tasks")}>
                        Tasks
                    </CNavLink>
                </CNavItem>
            </CNav>

            <CTabContent>
                <CTabPane visible={activeTab === "overview"}>
                    <p><strong>Description:</strong> {description}</p>
                    <p><strong>Number of entities:</strong> {num_entities}</p>

                    <CCard className="mb-4">
                        <CCardHeader>Schema Fields</CCardHeader>
                        <CCardBody>
                            <CTable striped hover responsive bordered>
                                <CTableHead>
                                    <CTableRow>
                                        <CTableHeaderCell>Field name</CTableHeaderCell>
                                        <CTableHeaderCell>Data type</CTableHeaderCell>
                                        <CTableHeaderCell>Params</CTableHeaderCell>
                                    </CTableRow>
                                </CTableHead>
                                <CTableBody>
                                    {fields.map((field, index) => (
                                        <CTableRow key={index}>
                                            <CTableDataCell>{field.name}</CTableDataCell>
                                            <CTableDataCell>{dataTypeMap[field.type] || field.type}</CTableDataCell>
                                            <CTableDataCell>
                                                {Object.entries(field.params).length > 0
                                                    ? Object.entries(field.params).map(([key, value]) => `${key}: ${value}`).join(", ")
                                                    : "—"}
                                            </CTableDataCell>
                                        </CTableRow>
                                    ))}
                                </CTableBody>
                            </CTable>
                        </CCardBody>
                    </CCard>

                    <CCard>
                        <CCardHeader>Indexes</CCardHeader>
                        <CCardBody>
                            <CTable striped hover responsive bordered>
                                <CTableHead>
                                    <CTableRow>
                                        <CTableHeaderCell>Field</CTableHeaderCell>
                                        <CTableHeaderCell>Index name</CTableHeaderCell>
                                        <CTableHeaderCell>Params</CTableHeaderCell>
                                    </CTableRow>
                                </CTableHead>
                                <CTableBody>
                                    {indexes.map((index, idx) => (
                                        <CTableRow key={idx}>
                                            <CTableDataCell>{index.field_name}</CTableDataCell>
                                            <CTableDataCell>{index.index_name}</CTableDataCell>
                                            <CTableDataCell>
                                                {Object.entries(index.params).map(([key, value]) => `${key}: ${value}`).join(", ")}
                                            </CTableDataCell>
                                        </CTableRow>
                                    ))}
                                </CTableBody>
                            </CTable>
                        </CCardBody>
                    </CCard>
                </CTabPane>

                <CTabPane visible={activeTab === "documents"}>
                    <CCard className="mb-3">
                        <CCardHeader>Add Document</CCardHeader>
                        <CCardBody className="d-flex gap-2 align-items-center">
                            <select
                                className="form-select"
                                value={selectedDocId}
                                onChange={(e) => setSelectedDocId(e.target.value)}
                            >
                                <option value="">-- Select a document --</option>
                                {availableDocuments.map((doc) => (
                                    <option key={doc.id} value={doc.id}>
                                        {doc.name}
                                    </option>
                                ))}
                            </select>

                            <button
                                className="btn btn-primary"
                                onClick={handleAddDocument}
                                disabled={!selectedDocId}
                            >
                                Add
                            </button>
                        </CCardBody>
                    </CCard>

                    <CCard>
                        <CCardHeader>Documents</CCardHeader>
                        <CCardBody>
                            <CTable striped hover responsive bordered>
                                <CTableHead>
                                    <CTableRow>
                                        <CTableHeaderCell>ID</CTableHeaderCell>
                                        <CTableHeaderCell>Name</CTableHeaderCell>
                                        <CTableHeaderCell>Path</CTableHeaderCell>
                                        <CTableHeaderCell>Status</CTableHeaderCell>
                                        <CTableHeaderCell>Actions</CTableHeaderCell>
                                    </CTableRow>
                                </CTableHead>

                                <CTableBody>
                                    {documentsList.length > 0 ? (
                                        documentsList.map((doc, index) => (
                                            <CTableRow key={index}>
                                                <CTableDataCell>{doc.id}</CTableDataCell>
                                                <CTableDataCell>{doc.name}</CTableDataCell>
                                                <CTableDataCell>{doc.path}</CTableDataCell>
                                                <CTableDataCell>{doc.status}</CTableDataCell>
                                                <CTableDataCell>
                                                    <button
                                                        className="btn btn-sm btn-danger"
                                                        onClick={() => handleRemoveDocument(doc.id)}
                                                    >
                                                        Remove
                                                    </button>
                                                </CTableDataCell>
                                            </CTableRow>
                                        ))
                                    ) : (
                                        <CTableRow>
                                            <CTableDataCell colSpan={5}>No any document</CTableDataCell>
                                        </CTableRow>
                                    )}
                                </CTableBody>

                            </CTable>
                        </CCardBody>
                    </CCard>
                </CTabPane>

                <CTabPane visible={activeTab === "tasks"}>
                    <CCard>
                        <CCardHeader>Indexing</CCardHeader>
                        <CCardBody>
                            <p>Perform indexing on this collection.</p>
                            <button
                                className="btn btn-success"
                                onClick={handleIndexCollection}
                                disabled={isIndexing}
                            >
                                {isIndexing ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-2" role="status"
                                              aria-hidden="true"></span>
                                        Indexing...
                                    </>
                                ) : ("Index")}
                            </button>
                        </CCardBody>
                    </CCard>
                    <br/>
                    <CCard>
                        <CCardHeader>Flushing</CCardHeader>
                        <CCardBody>
                            <p>Flush on this collection.</p>
                            <button
                                className="btn btn-success"
                                onClick={handleFlushCollection}
                                disabled={isFlushing}
                            >
                                {isFlushing ? (
                                    <>
                                        <span className="spinner-border spinner-border-sm me-2" role="status"
                                              aria-hidden="true"></span>
                                        Flushing...
                                    </>
                                ) : ("Flush")}
                            </button>
                        </CCardBody>
                    </CCard>
                </CTabPane>
            </CTabContent>
        </>
    )
}

root.render(<App model={model} csrf_token={csrf_token}/>);
