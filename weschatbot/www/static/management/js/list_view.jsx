import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {CBadge, CFormSwitch} from "@coreui/react";


function SearchBox({search_url, keyword, page_size}) {
    let kkw = ""
    if (keyword === "null" || keyword === null) {
        kkw = ""
    } else {
        kkw = keyword
    }

    const [kw, setKw] = useState(kkw)

    const search = () => {
        const url = kw && `${search_url}?keyword=${kw}&page=1&page_size=${page_size}` || `${search_url}?page=1&page_size=${page_size}`
        window.location.replace(url)
    }

    return (
        <>
            <div className={"row g-2"}>
                <div className={"col-auto"}>
                    <input type={"text"} className={"form-control"} id={"inputKeyword"} value={kw}
                           onChange={(e) => setKw(e.target.value)} placeholder={"keyword ..."}/>
                </div>
                <div className={"col-auto"}>
                    <button className={"btn btn-primary mb-3"} onClick={search}>Search</button>
                </div>
            </div>
        </>
    )
}


function ActionColumn({item}) {
    return (
        <>
            <div className={"btn-group"}>
                {
                    item.detail_url !== null &&
                    <a href={item.detail_url} className={"btn btn-sm btn-outline-secondary"}
                       style={{height: "25px", padding: "2px", width: "25px"}}>
                    <span><i className={"bi bi-search"}></i>
                    </span>
                    </a>
                }
                {
                    item.update_url !== null &&
                    <a href={item.update_url} className={"btn btn-sm btn-outline-secondary"}
                       style={{height: "25px", padding: "2px", width: "25px"}}>
                    <span><i className={"bi bi-pencil"}></i>
                    </span>
                    </a>
                }
                {
                    item.delete_url !== null &&
                    <a href={item.delete_url} className={"btn btn-sm btn-outline-secondary"}
                       style={{height: "25px", padding: "2px", width: "25px"}}>
                    <span><i className={"bi bi-trash"}></i>
                    </span>
                    </a>
                }
            </div>
        </>
    )
}

function AddBox({add_url}) {
    const add = () => {
        window.location.replace(add_url)
    }

    return (
        <>
            {add_url !== null &&
                <button type={"button"} className={"btn btn-outline-success"} onClick={add}>New</button>
            }
        </>
    )
}

function Pagination({search_url, page, page_size, total, keyword}) {
    const num_of_page = Math.ceil(total / page_size)
    const search = (page_index) => {
        let url = `${search_url}?page=${page_index}&page_size=${page_size}`
        if (keyword !== null) {
            url = `${url}&keyword=${keyword}`
        }

        window.location.replace(url)
    }

    const prev = () => {
        search(page - 1)
    }

    const next = () => {
        search(page + 1)
    }

    return (
        <>
            <nav aria-label={"Pagination"}>
                <ul className={"pagination"}>
                    {page > 1 &&
                        <li className={"page-item"}>
                            <a className={"page-link"} href={"#"} aria-label={"Previous"} onClick={prev}>
                                <span aria-hidden={"true"}>&laquo;</span>
                            </a>
                        </li>
                    }

                    <li className={"page-item"}>
                        <a className={"page-link"}
                           href={"#"}>{(page - 1) * page_size + 1} - {Math.min(page * page_size, total)} of {total}</a>
                    </li>

                    {page < num_of_page &&
                        <li className={"page-item"}>
                            <a className={"page-link"} href={"#"} aria-label={"Next"} onClick={next}>
                                <span aria-hidden={"true"}>&raquo;</span>
                            </a>
                        </li>
                    }
                </ul>
            </nav>
        </>
    )
}


function DataListView({items, data_types, list_fields}) {
    const fieldHelper = (data, data_type) => {
        switch (data_type) {
            case "boolean":
                return (
                    <CFormSwitch
                        checked={data}
                        onChange={(e) => {
                            onToggle && onToggle(e.target.checked)
                        }}
                        style={{fontSize: '1rem'}}
                    />
                )

            case "relationship_many":
                return (
                    <>
                        {data.map((item, idx) => (
                            <CBadge
                                key={idx}
                                color="secondary"
                                className="me-1"
                                style={{fontSize: '0.8rem', padding: '0.5em 0.75em'}}
                            >
                                {item}
                            </CBadge>
                        ))}
                    </>
                )
            default:
                return <span>{data}</span>
        }
    }

    return (
        <>
            <table className={"table table-bordered table-hover table-sm"}>
                <thead>
                <tr>
                    <th scope={"col"}>#</th>
                    {
                        list_fields.map(x => {
                            return <th key={`hcol_${x}`} scope={"col"}>{x}</th>
                        })
                    }
                </tr>
                </thead>
                <tbody>
                {
                    items.map((x, index) => {
                        return <tr key={`tb_row_${index}`}>
                            <td>
                                <ActionColumn item={x}></ActionColumn>
                            </td>
                            {
                                list_fields.map((field) => {
                                    return <td key={`${x.id}_${field}`}>{fieldHelper(x[field], data_types[field])}</td>
                                })
                            }
                        </tr>
                    })
                }
                </tbody>
            </table>
        </>
    )
}

function App({model}) {
    const title = model["title"]
    const data_types = model["data_types"]
    const list_fields = model["list_fields"]
    const items = model["items"]
    const search_url = model["search_url"]
    const add_url = model["add_url"]
    const pagination = model["pagination"]
    const keyword = model["keyword"]
    return (
        <>
            <h4>{title}</h4>
            <br/>
            <div className={"row"}>
                <div className={"col-md-6"}>
                    <SearchBox search_url={search_url} keyword={keyword}
                               page_size={pagination["page_size"]}></SearchBox>
                </div>
                <div className={"col-md-6"}>
                    <div className={"float-end"}>
                        <AddBox add_url={add_url}></AddBox>
                    </div>
                </div>
            </div>

            <DataListView data_types={data_types} items={items} list_fields={list_fields}></DataListView>
            <Pagination search_url={search_url} keyword={keyword} total={pagination["total"]} page={pagination["page"]}
                        page_size={pagination["page_size"]}></Pagination>
        </>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)