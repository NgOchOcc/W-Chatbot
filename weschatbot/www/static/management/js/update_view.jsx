import {CSRFToken} from "./utils";
import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import Select from "react-select";


function UpdateFormHelper({name, type, init_value, relationships, select_items}) {
    switch (type) {
        case "select": {
            const options = select_items[name].map((item) => {
                return {value: item, label: item}
            })

            const selectedValue = {value: init_value, label: init_value}

            const [selected, setSelected] = useState(selectedValue)

            const onSelectChangeHandler = (s) => {
                setSelected(s)
            }

            return (
                <>
                    <div className={"form-group"}>
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

            const selectedValue = {value: init_value.id, label: init_value.name}

            const [selected, setSelected] = useState(selectedValue)

            const onSelectChangeHandler = (s) => {
                setSelected(s)
            }

            return (
                <>
                    <div className={"form-group"}>
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

            const [value, setValue] = useState(init_value)

            const selectedValue = value.map((item) => {
                return {value: item.id, label: item.name}
            })

            const [selected, setSelected] = useState(selectedValue)

            const onSelectChangeHandler = (s) => {
                setSelected(s)
                setValue(s.map((item) => {
                    return {id: item.id, name: item.label}
                }))
            }

            return (
                <>
                    <div className={"form-group"}>
                        <Select options={options} name={name} closeMenuOnSelect={false} isMulti value={selected}
                                onChange={onSelectChangeHandler}></Select>
                    </div>
                </>
            )
        }
        case "boolean": {
            const [value, setValue] = useState(Boolean(init_value))
            return (
                <>
                    <div className={"form-group"}>
                        <input className="form-check-input" name={name} type="checkbox" value={value} checked={value}
                               onChange={(e) =>
                                   setValue(e.target.checked)
                               }></input>
                    </div>
                </>
            )
        }
        case "text": {
            const [value, setValue] = useState(String(init_value))
            return (
                <>
                    <div className={"form-group"}>
                        {/*<input className="form-check-input" name={name} type="checkbox" value={value} checked={value}*/}
                        {/*       onChange={(e) =>*/}
                        {/*           setValue(e.target.checked)*/}
                        {/*       }></input>*/}

                        <textarea className="form-control" name={name} disabled={false} value={value}
                                  onChange={(e) => setValue(e.target.value)}
                                  rows="5">{value}</textarea>
                    </div>
                </>
            )
        }
        default: {
            const [value, setValue] = useState(String(init_value))
            return (
                <input className={"form-control"} name={name} type={"input"} value={value}
                       onChange={(e) => setValue(e.target.value)}></input>
            )
        }
    }
}


function UpdateView({model, csrf_token}) {
    const relationships = model.relationships
    const select_items = model.select_items
    return (
        <>
            <div className={"row"}>
                <div className={"col-md-6"}>
                    <form name={"updateForm"} className={"smaller-font"} method={"POST"}
                          encType={"multipart/form-data"}>
                        <CSRFToken csrf_token={csrf_token}></CSRFToken>
                        {
                            model["update_fields"].map((field) => {
                                return (
                                    <div className={"mb-3 form-group"}>
                                        <label><strong>{field}</strong></label>
                                        <UpdateFormHelper name={field} type={model["data_types"][field]}
                                                          init_value={model["item"][field]}
                                                          relationships={relationships}
                                                          select_items={select_items}></UpdateFormHelper>
                                    </div>
                                )
                            })
                        }
                        <button className={"btn btn-primary me-2"} type={"submit"}><i className={"bi bi-save"}></i> Save
                        </button>
                        <button className={"btn btn-outline-secondary"} type={"button"} onClick={() => history.back()}>
                            <i className={"bi bi-x-lg"}></i> Cancel
                        </button>
                    </form>
                </div>
            </div>
        </>
    )
}


function App({model, csrf_token}) {
    return (
        <>
            <h4>{model.title} :: {model.item.name}</h4>
            <br/>
            <UpdateView model={model} csrf_token={csrf_token}></UpdateView>
        </>
    )
}

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)
const csrf_token = document.getElementById("csrf_token").innerText.trim()

root.render(<App model={model} csrf_token={csrf_token}/>)
