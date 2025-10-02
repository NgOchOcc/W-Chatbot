import {createRoot} from "react-dom/client";
import React, {useEffect, useState} from "react";
import {
    CBadge,
    CButton,
    CButtonGroup,
    CCard,
    CCardBody,
    CCardHeader, CCollapse,
    CFormInput,
    CInputGroup,
    CModal,
    CModalBody,
    CModalFooter,
    CModalHeader,
    CNav,
    CNavItem,
    CNavLink,
    CPagination,
    CPaginationItem, CSpinner,
    CTabContent,
    CTable,
    CTableBody,
    CTableDataCell,
    CTableHead,
    CTableHeaderCell,
    CTableRow,
    CTabPane,
} from "@coreui/react";
import CIcon from "@coreui/icons-react";
import {cilCloudDownload, cilSearch, cilTrash} from "@coreui/icons";
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


function ActionColumn({item, onDelete}) {
    const [visibleDetail, setVisibleDetail] = useState(false);
    const [visibleConfirm, setVisibleConfirm] = useState(false);

    return (
        <>
            <CButtonGroup>
                <CButton
                    color="secondary"
                    variant="outline"
                    style={{height: "25px", padding: "0px", width: "25px"}}
                    onClick={() => setVisibleDetail(true)}
                >
                    <CIcon icon={cilSearch} size="md"/>
                </CButton>
                <CButton
                    color="secondary"
                    variant="outline"
                    style={{height: "25px", padding: "0px", width: "25px"}}
                    onClick={() => setVisibleConfirm(true)}
                >
                    <CIcon icon={cilTrash} size="md"/>
                </CButton>
            </CButtonGroup>

            <CModal visible={visibleDetail} onClose={() => setVisibleDetail(false)} size="lg">
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
                    <CButton color="secondary" onClick={() => setVisibleDetail(false)}>Close</CButton>
                </CModalFooter>
            </CModal>

            <CModal visible={visibleConfirm} onClose={() => setVisibleConfirm(false)}>
                <CModalHeader>Delete Confirm</CModalHeader>
                <CModalBody>
                    Are you sure to delete entity ID: <strong>{item["row_id"]}</strong>?
                </CModalBody>
                <CModalFooter>
                    <CButton color="danger" onClick={() => {
                        onDelete(item);
                        setVisibleConfirm(false);
                    }}>Delete</CButton>
                    <CButton color="secondary" onClick={() => setVisibleConfirm(false)}>Cancel</CButton>
                </CModalFooter>
            </CModal>
        </>
    );
}

function NotFoundMilvusTasksPage() {
    return (
        <span>Collection is not exist int Milvus</span>
    )
}

function NotFoundMilvusEntitiesPage({collectionId}) {
    return (
        <span>Collection is not exist int Milvus</span>
    )
}

function NotFoundMilvusOverviewPage() {
    return (
        <span>Collection is not exist int Milvus</span>
    )
}

function MilvusOverviewPage({fields, indexes, description, num_entities}) {
    return (
        <>
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
                        {Object.keys(fields).length !== 0 &&
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
                        }

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
                        {Object.keys(indexes).length !== 0 &&
                            <CTableBody>
                                {indexes.map((index, idx) => (
                                    <CTableRow key={idx}>
                                        <CTableDataCell>{index["field_name"]}</CTableDataCell>
                                        <CTableDataCell>{index["index_name"]}</CTableDataCell>
                                        <CTableDataCell>
                                            {Object.entries(index.params).map(([key, value]) => `${key}: ${value}`).join(", ")}
                                        </CTableDataCell>
                                    </CTableRow>
                                ))}
                            </CTableBody>
                        }
                    </CTable>
                </CCardBody>
            </CCard>
        </>
    )
}

function MilvusEntitiesPage({collectionId}) {
    const [entities, setEntities] = useState([])
    const [search, setSearch] = useState("")
    const [tokens, setTokens] = useState([""])
    const [currentPage, setCurrentPage] = useState(0)
    const [loading, setLoading] = useState(false)


    const fetchEntities = (callback, token = "") => {
        fetch(`/management/ViewModelCollection/collection_entities?collection_id=${collectionId}&search=${encodeURIComponent(search)}&token=${encodeURIComponent(token)}`)
            .then((res) => res.json())
            .then((data) => {
                setEntities(data["data"])
                callback(data["next_token"])
            })
    }

    const handlePrevious = () => {
        console.log("Previous clicked")
        let res = tokens[currentPage - 1]
        fetchEntities((nToken) => {
            setCurrentPage(Math.max(currentPage - 1, 0))
        }, res)
    }

    const handleNext = () => {
        console.log("Next clicked")
        fetchEntities((nToken) => {
            if (nToken !== null) {
                if (!tokens.includes(nToken)) {
                    tokens.push(nToken)
                    setTokens(tokens)

                }
            }
            setCurrentPage(Math.min(currentPage + 1, tokens.length - 1))
        }, tokens[currentPage + 1])
    }

    useEffect(() => {
        fetchEntities((nToken) => {
            tokens.push(nToken)
            setTokens(tokens)
        }, "")
    }, [])

    const handleSearch = () => {
        fetchEntities((nToken) => {
            tokens.push(nToken)
            setTokens(tokens)
        }, "")
    }

    const deleteItem = (collection_id) => async (item) => {
        const formData = new FormData();
        formData.append("collection_id", collection_id)
        formData.append("row_id", item["row_id"])

        setLoading(true)
        try {
            const response = await fetch("/management/ViewModelCollection/delete_entities", {
                headers: {
                    "X-CSRFToken": csrf_token,
                },
                method: "POST",
                body: formData,
            });

            const result = await response.json();

            if (response.ok && result.status === "success") {
                fetchEntities(() => {
                }, tokens[currentPage])

            } else {
                alert("Failed deleted entities! : " + result.message);
            }
        } catch (error) {
            alert("Error in API calling: " + error.message);
        } finally {
            setLoading(false)
        }
    };


    return (
        <>
            <div className="position-relative">
                {loading && (
                    <div className="overlay">
                        <CSpinner color="primary"/>
                    </div>
                )}
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
                                onClick={handleSearch}
                            >
                                Search
                            </CButton>
                        </CInputGroup>

                        <div style={{maxHeight: "620px", overflowY: "auto"}}>
                            <CTable striped hover responsive small>
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
                                                <ActionColumn item={item} onDelete={deleteItem(collectionId)}/>
                                            </CTableDataCell>
                                            <CTableDataCell style={{width: "15%"}}><span
                                                style={{fontSize: "0.9rem"}}>{item["row_id"]}</span></CTableDataCell>
                                            <CTableDataCell style={{width: "80%"}}><span
                                                style={{fontSize: "0.9rem"}}>{item["text"]}</span></CTableDataCell>
                                        </CTableRow>
                                    ))}
                                </CTableBody>
                            </CTable>
                        </div>

                        <br/>
                        <CPagination aria-label="Page navigation">
                            {currentPage > 0 &&
                                <CPaginationItem
                                    aria-label="Previous"
                                    style={{cursor: "pointer"}}
                                    onClick={handlePrevious}
                                >
                                    <span aria-hidden="true">&laquo;</span>
                                </CPaginationItem>
                            }
                            {currentPage < tokens.length - 1 &&
                                <CPaginationItem
                                    aria-label="Next"
                                    style={{cursor: "pointer"}}
                                    onClick={handleNext}
                                >
                                    <span aria-hidden="true">&raquo;</span>
                                </CPaginationItem>
                            }
                        </CPagination>
                    </CCardBody>
                </CCard>
            </div>
        </>
    );
}


function AddDocumentBox({handleAddDocument}) {
    const [selectedDocId, setSelectedDocId] = useState("")
    const [availableDocuments, setAvailableDocuments] = useState([])
    const [visible, setVisible] = useState(false)

    useEffect(() => {
        fetch("/management/ViewModelCollection/available_documents", {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrf_token,
            },
        })
            .then((res) => {
                if (!res.ok) throw new Error("Failed to load documents")
                return res.json()
            })
            .then((data) => {
                setAvailableDocuments(data)
            })
            .catch((err) => {
                console.error("Error loading documents:", err)
            })
    }, [])

    return (
        <CCard className="mb-3">
            <CCardHeader>
                Add Document
                <CButton
                    color="link"
                    size="sm"
                    className="float-end"
                    style={{textDecoration: 'none'}}
                    onClick={() => setVisible(!visible)}
                >
                    {visible ? 'Hide' : 'Show'}
                </CButton>
            </CCardHeader>

            <CCollapse visible={visible}>
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
                        onClick={() => handleAddDocument(selectedDocId)}
                        disabled={!selectedDocId}
                    >
                        Add
                    </button>
                </CCardBody>
            </CCollapse>
        </CCard>
    )
}


function ListDocumentsActions(
    {
        item,
        hasDelete = false, onDelete = null, confirmDelete = false, confirmMessage = "Are you sure?",
        hasDownload = false, onDownload = null
    }) {

    const [visibleConfirm, setVisibleConfirm] = useState(false)

    function retOnClickDelete() {
        if (confirmDelete) {
            return () => setVisibleConfirm(true)
        }
        return () => onDelete(item)
    }

    return (
        <>
            <CButtonGroup>
                {hasDelete &&
                    <CButton
                        color="secondary"
                        variant="outline"
                        style={{height: "25px", padding: "0px", width: "25px"}}
                        onClick={retOnClickDelete()}
                    >
                        <CIcon icon={cilTrash} size="md"/>
                    </CButton>
                }
                {hasDownload &&
                    <CButton
                        color="secondary"
                        variant="outline"
                        style={{height: "25px", padding: "0px", width: "25px"}}
                        onClick={onDownload}
                    >
                        <CIcon icon={cilCloudDownload}/>
                    </CButton>
                }
            </CButtonGroup>

            <CModal visible={visibleConfirm} onClose={() => setVisibleConfirm(false)}>
                <CModalHeader>Delete Confirm</CModalHeader>
                <CModalBody>
                    {confirmMessage}
                </CModalBody>
                <CModalFooter>
                    <CButton color="danger" onClick={() => {
                        onDelete(item);
                        setVisibleConfirm(false);
                    }}>Delete</CButton>
                    <CButton color="secondary" onClick={() => setVisibleConfirm(false)}>Cancel</CButton>
                </CModalFooter>
            </CModal>
        </>
    )
}


function StatusBadge({status}) {
    let color = 'secondary'
    let label = status

    switch (status) {
        case 'active':
            color = 'success'
            label = 'Active'
            break
        case 'done':
            color = 'success'
            label = 'Done'
            break
        case 'inactive':
            color = 'secondary'
            label = 'Inactive'
            break
        case 'new':
            color = 'secondary'
            label = 'new'
            break
        case 'pending':
            color = 'warning'
            label = 'Pending'
            break
        case 'error':
            color = 'danger'
            label = 'Error'
            break
        case 'processing':
            color = 'info'
            label = 'Processing'
            break
        case 'in progress':
            color = 'info'
            label = 'Processing'
            break
        default:
            color = 'dark'
            label = status || 'Unknown'
    }

    return <CBadge color={color} style={{fontSize: "0.9rem"}}>{label}</CBadge>
}

function ListDocuments({documentsList, handleRemoveDocument}) {
    return (
        <>
            <CCard>
                <CCardHeader>Documents</CCardHeader>
                <CCardBody>
                    <div style={{maxHeight: "550px", overflowY: "auto"}}>
                        <CTable striped hover responsive bordered>
                            <CTableHead>
                                <CTableRow>
                                    <CTableHeaderCell>#</CTableHeaderCell>
                                    <CTableHeaderCell>ID</CTableHeaderCell>
                                    <CTableHeaderCell>Name</CTableHeaderCell>
                                    <CTableHeaderCell>Path</CTableHeaderCell>
                                    <CTableHeaderCell>Status</CTableHeaderCell>

                                </CTableRow>
                            </CTableHead>

                            <CTableBody>
                                {documentsList.length > 0 ? (
                                    documentsList.map((doc, index) => (
                                        <CTableRow key={index}>
                                            <CTableDataCell>
                                                <ListDocumentsActions
                                                    item={doc.id} hasDelete={true}
                                                    confirmDelete={true}
                                                    onDelete={handleRemoveDocument}
                                                >
                                                </ListDocumentsActions>
                                            </CTableDataCell>
                                            <CTableDataCell
                                                style={{minWidth: '50px', fontSize: "0.9rem"}}>{doc.id}</CTableDataCell>
                                            <CTableDataCell
                                                style={{
                                                    minWidth: '200px',
                                                    fontSize: "0.9rem"
                                                }}>{doc.name}</CTableDataCell>
                                            <CTableDataCell style={{
                                                wordBreak: 'break-word',
                                                whiteSpace: 'pre-wrap',
                                                fontSize: "0.9rem"
                                            }}>{doc.path}</CTableDataCell>
                                            <CTableDataCell><StatusBadge
                                                status={doc.status}></StatusBadge></CTableDataCell>

                                        </CTableRow>
                                    ))
                                ) : (
                                    <CTableRow>
                                        <CTableDataCell colSpan={5}>No any document</CTableDataCell>
                                    </CTableRow>
                                )}
                            </CTableBody>

                        </CTable>
                    </div>
                </CCardBody>
            </CCard>
        </>
    )
}

function CollectionInfoPage({data}) {
    const [activeTab, setActiveTab] = useState("documents")
    const {collection_id, collection_name, description, num_entities, fields, indexes, status, documents = []} = data
    const [documentsList, setDocumentsList] = useState(documents)
    const [refreshFlag, setRefreshFlag] = useState(0)
    const [isIndexing, setIsIndexing] = useState(status === "running")
    const [isFlushing, setIsFlushing] = useState(false)


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


    const handleAddDocument = (collection_id) => (selectedDocId) => {
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


    const handleRemoveDocument = (docId) => {
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
                    {status === 404 &&
                        <NotFoundMilvusOverviewPage></NotFoundMilvusOverviewPage>
                        ||
                        <MilvusOverviewPage description={description} indexes={indexes} fields={fields}
                                            num_entities={num_entities}></MilvusOverviewPage>
                    }
                </CTabPane>

                <CTabPane visible={activeTab === "documents"}>
                    <AddDocumentBox handleAddDocument={handleAddDocument(collection_id)}></AddDocumentBox>
                    <ListDocuments documentsList={documentsList}
                                   handleRemoveDocument={handleRemoveDocument}></ListDocuments>
                </CTabPane>

                <CTabPane visible={activeTab === "tasks"}>
                    {status === 404 &&
                        <NotFoundMilvusTasksPage></NotFoundMilvusTasksPage>
                        ||
                        <>
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
                        </>
                    }

                </CTabPane>
                <CTabPane visible={activeTab === "entities"}>
                    {status !== 404 &&
                        <MilvusEntitiesPage collectionId={collection_id}></MilvusEntitiesPage>
                        ||
                        <NotFoundMilvusEntitiesPage collectionId={collection_id}></NotFoundMilvusEntitiesPage>
                    }

                </CTabPane>
            </CTabContent>
        </>
    )
}

root.render(<App model={model} csrf_token={csrf_token}/>);
