import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {
    CAlert,
    CButton,
    CCol,
    CFormSelect,
    CRow,
    CSpinner,
    CTable,
    CTableBody,
    CTableDataCell,
    CTableHead,
    CTableHeaderCell,
    CTableRow
} from "@coreui/react";
import {Pagination} from "./pagination";

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)
const csrf_token = document.getElementById("csrf_token").innerText.trim()


function LoadCollectionBox({collectionName, loadUrl, pageSize, list_collections, onLoad}) {
    const [collections, setCollections] = useState(list_collections);
    const [selectedCollection, setSelectedCollection] = useState(collectionName || "");

    const search = () => {
        if (onLoad) {
            onLoad(selectedCollection);
        }
    }

    return (
        <CRow className="g-2 mb-3">
            <CCol xs="auto">
                <CFormSelect
                    style={{minWidth: "250px"}}
                    value={selectedCollection}
                    onChange={(e) => setSelectedCollection(e.target.value)}
                >
                    <option value="">-- select collection name --</option>
                    {collections.map((name, index) => (
                        <option key={index} value={name}>
                            {name}
                        </option>
                    ))}
                </CFormSelect>
            </CCol>
            <CCol xs="auto">
                <CButton color="primary" onClick={search}>
                    Load
                </CButton>
            </CCol>
        </CRow>
    )
}


function EntityTable({entities}) {
    return (
        <CTable striped hover responsive bordered>
            <CTableHead>
                <CTableRow>
                    <CTableHeaderCell>ID</CTableHeaderCell>
                    <CTableHeaderCell>Content</CTableHeaderCell>
                    <CTableHeaderCell>Document file</CTableHeaderCell>
                </CTableRow>
            </CTableHead>
            <CTableBody>
                {entities.map((entity, index) => (
                    <CTableRow key={index}>
                        <CTableDataCell>{entity.id}</CTableDataCell>
                        <CTableDataCell>{entity.content}</CTableDataCell>
                        <CTableDataCell>{entity.document_file}</CTableDataCell>
                    </CTableRow>
                ))}
            </CTableBody>
        </CTable>
    );
}


function App({model, csrf_token}) {
    const collections = model["collections"];
    const search_url = "/management/ViewModelCollections/entities";
    const pagination = {
        page: 1,
        page_size: 10,
        total: 100,
    };

    const [entities, setEntities] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [keyword, setKeyword] = useState("");

    const handleLoadEntities = async (collectionName) => {
        setKeyword(collectionName);
        setLoading(true);
        setError("");
        try {
            const response = await fetch(
                `${search_url}?collection_name=${collectionName}&start_id=${pagination.page}&limit=${pagination.page_size}`,
                {
                    method: "GET",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": csrf_token,
                    },
                }
            )
            if (!response.ok) throw new Error("Can not load data");
            const data = await response.json();
            setEntities(data)
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <>
            <h4>Collections</h4>
            <LoadCollectionBox
                loadUrl={search_url}
                collectionName={keyword}
                pageSize={pagination.page_size}
                list_collections={collections}
                onLoad={handleLoadEntities}
            />

            {
                loading && <CSpinner color="primary"/>
            }
            {
                error && <CAlert color="danger">{error}</CAlert>
            }

            <EntityTable entities={entities}/>

            <Pagination
                search_url={search_url}
                keyword={keyword}
                total={pagination.total}
                page={pagination.page}
                page_size={pagination.page_size}
            />
        </>
    )
}

root.render(<App model={model} csrf_token={csrf_token}/>)
