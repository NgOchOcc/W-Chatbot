import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {CSRFToken} from "./utils";
import Select from "react-select";
import {CButton, CFormInput, CFormLabel} from "@coreui/react";


function AddFormHelper({name, data_type, relationships = {}, select_items = {}}) {
    switch (data_type) {
        case "select": {
            const options = select_items[name].map((item) => {
                return {value: item, label: item}
            })

            const selectedValue = {value: -1, label: ""}

            const [selected, setSelected] = useState(selectedValue)

            const onSelectChangeHandler = (s) => {
                setSelected(s)
            }

            return (
                <>
                    <div className={"form-group"}>
                        <label>{name}</label>
                        <Select options={options} name={name} closeMenuOnSelect={true} value={selected}
                                onChange={onSelectChangeHandler}></Select>
                    </div>
                </>
            )
        }
        case "relationship_one": {
            const options = relationships[name].map((item) => {
                return {value: item.id, label: item.name}
            })

            const selectedValue = {value: -1, label: ""}

            const [selected, setSelected] = useState(selectedValue)

            const onSelectChangeHandler = (s) => {
                setSelected(s)
            }

            return (
                <>
                    <div className={"form-group"}>
                        <label>{name}</label>
                        <Select options={options} name={name} closeMenuOnSelect={true} value={selected}
                                onChange={onSelectChangeHandler}></Select>
                    </div>
                </>
            )
        }
        case "relationship_many": {
            const options = relationships[name].map((item) => {
                return {value: item.id, label: item.name}
            })

            const selectedValue = {value: -1, label: null}

            const [selected, setSelected] = useState()

            const onSelectChangeHandler = (s) => {
                setSelected(s)
            }

            return (
                <>
                    <div className={"form-group"}>
                        <label>{name}</label>
                        <Select options={options} name={name} closeMenuOnSelect={false} isMulti value={selected}
                                onChange={onSelectChangeHandler}></Select>
                    </div>
                </>
            )
        }
        case "file_upload": {
            return (
                <div>
                    <label htmlFor={`file_${name}`} className="form-label">{name}</label>
                    <input className="form-control" type="file" id={`file_${name}`} name={name}/>
                </div>
            )
        }
        default:
            return (
                <>
                    <div className={"form-group"}>
                        <label>{name}</label>
                        <input type={"text"} className={"form-control"} name={name}/>
                    </div>
                </>
            )
    }
}


function App({model, csrf_token}) {
    const title = model["title"]
    const add_fields = model["add_fields"]
    const data_types = model["data_types"]
    const relationships = model["relationships"] || {}
    const select_items = model["select_items"] || {}

    return (
        <>
            <h4>{title}</h4>
            <br/>
            <div className={"row"}>
                <div className={"col-md-6"}>
                    <form name={"addForm"} method={"post"} encType={"multipart/form-data"}>
                        <CSRFToken csrf_token={csrf_token}></CSRFToken>
                        {add_fields.map(x => {
                            return (
                                <div className={"mb-3 form-group"}>
                                    <AddFormHelper name={x} data_type={data_types[x]}
                                                   relationships={relationships}
                                                   select_items={select_items}></AddFormHelper>
                                </div>
                            )
                        })}
                        <button className={"btn btn-success me-1"} type={"submit"}>
                            <i className={"bi bi-plus-lg"}></i> Add
                        </button>
                        <button type={"button"} className={"btn btn-outline-danger"} onClick={() => history.back()}><i
                            className={"bi bi-x-lg"}></i> Cancel
                        </button>
                    </form>
                </div>
            </div>
        </>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)
const csrf_token = document.getElementById("csrf_token").innerText.trim()

root.render(<App model={model} csrf_token={csrf_token}/>)
