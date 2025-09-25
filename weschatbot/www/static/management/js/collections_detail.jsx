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
    CTabPane, CFormInput, CButtonGroup, CButton, CModal, CModalHeader, CModalBody, CModalFooter, CInputGroup,
} from "@coreui/react";
import CIcon from "@coreui/icons-react";
import {cilSearch} from "@coreui/icons";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import ReactMarkdown from "react-markdown";

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


function ActionColumn({item}) {
    const [visible, setVisible] = useState(false);

    return (
        <>
            <CButtonGroup>
                <CButton
                    color="secondary"
                    size="sm"
                    variant="outline"
                    style={{height: "25px", padding: "2px", width: "25px"}}
                    onClick={() => setVisible(true)}
                >
                    <CIcon icon={cilSearch} size="sm"/>
                </CButton>
            </CButtonGroup>

            <CModal visible={visible} onClose={() => setVisible(false)} size="lg">
                <CModalHeader>Entity Detail</CModalHeader>
                <CModalBody>
                    <p><strong>Row ID:</strong> {item["row_id"]}</p>
                    <p><strong>Text:</strong>
                        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                            {item["text"]}
                        </ReactMarkdown>
                    </p>
                </CModalBody>
                <CModalFooter>
                    <CButton color="secondary" onClick={() => setVisible(false)}>Close</CButton>
                </CModalFooter>
            </CModal>
        </>
    );
}

function MilvusEntitiesPage({collectionId}) {
    const [entities, setEntities] = useState([]);
    const [search, setSearch] = useState("");

    const fetchEntities = () => {
        fetch(`/management/ViewModelCollection/collection_entities?collection_id=${collectionId}&search=${encodeURIComponent(search)}`)
            .then((res) => res.json())
            .then((data) => {
                console.log(data);
                setEntities(data["data"])
            });
    }

    useEffect(() => {
        fetchEntities()
    }, [])

    const handleSearch = () => {
        console.log(search)
        fetchEntities()
    }

    return (
        <>
            <CCard>
                <CCardHeader>Milvus Entities</CCardHeader>
                <CCardBody>
                    <CInputGroup className="mb-3" style={{maxWidth: "400px"}}>
                        <CFormInput
                            type="text"
                            placeholder="Search text..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />
                        <CButton
                            type="button"
                            color="primary"
                            onClick={() => {
                                handleSearch()
                            }}
                        >
                            Search
                        </CButton>
                    </CInputGroup>
                    <div style={{maxHeight: "680px", overflowY: "auto"}}>
                        <CTable striped hover responsive>
                            <CTableHead>
                                <CTableRow>
                                    <CTableHeaderCell style={{width: "5%"}}>#</CTableHeaderCell>
                                    <CTableHeaderCell style={{width: "15%"}}>Row ID</CTableHeaderCell>
                                    <CTableHeaderCell style={{width: "80%"}}>Text</CTableHeaderCell>
                                </CTableRow>
                            </CTableHead>
                            <CTableBody>
                                {entities.map((item, index) => (
                                    <CTableRow key={index}>
                                        <CTableDataCell style={{width: "5%"}}>
                                            <ActionColumn item={item}></ActionColumn>
                                        </CTableDataCell>
                                        <CTableDataCell style={{width: "15%"}}>{item["row_id"]}</CTableDataCell>
                                        <CTableDataCell style={{width: "80%"}}>{item["text"]}</CTableDataCell>
                                    </CTableRow>
                                ))}
                            </CTableBody>
                        </CTable>
                    </div>
                </CCardBody>
            </CCard>
        </>
    );
}

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
        fetch("/management/ViewModelCollection/available_documents", {
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

    useEffect(() => {
        const indexingFlag = localStorage.getItem("isIndexing_" + collection_id)
        if (indexingFlag === "true") {
            pollCollectionStatus()
        }
    }, [])


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
                    localStorage.setItem("isIndexing_" + collection_id, "true")
                    setTimeout(() => {
                        pollCollectionStatus()
                    }, 5000)
                } else {
                    alert("Failed: " + data.message)
                }
            })
            .catch((err) => {
                alert("Error: " + err)
            })
    }

    function pollCollectionStatus() {

        const interval = setInterval(() => {
            fetch("/management/ViewModelCollection/check_collection_indexing?collection_id=" + collection_id, {
                method: "GET",
                headers: {
                    "X-CSRFToken": csrf_token,
                },
            })
                .then((res) => res.json())
                .then((data) => {
                    if (data.status === "success" && data.collection_status === "done") {
                        clearInterval(interval)
                        setIsIndexing(false)
                        console.log("Collection indexing completed.")
                    }
                })
                .catch((err) => {
                    clearInterval(interval)
                    alert("Error checking status: " + err)
                })
        }, 5000)
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
                    <CNavLink active={activeTab === "entities"} onClick={() => setActiveTab("entities")}>
                        Entities
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
                                                <CTableDataCell style={{minWidth: '50px'}}>{doc.id}</CTableDataCell>
                                                <CTableDataCell style={{minWidth: '200px'}}>{doc.name}</CTableDataCell>
                                                <CTableDataCell style={{
                                                    wordBreak: 'break-word',
                                                    whiteSpace: 'pre-wrap'
                                                }}>{doc.path}</CTableDataCell>
                                                <CTableDataCell
                                                    style={{minWidth: '100px'}}>{doc.status}</CTableDataCell>
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
                <CTabPane visible={activeTab === "entities"}>
                    <MilvusEntitiesPage collectionId={collection_id}></MilvusEntitiesPage>
                </CTabPane>
            </CTabContent>
        </>
    )
}

root.render(<App model={model} csrf_token={csrf_token}/>);
