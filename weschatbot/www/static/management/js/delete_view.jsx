import {createRoot} from "react-dom/client";
import React from "react";
import {CSRFToken} from "./utils";


function DeleteView({csrf_token, item}) {
    return (
        <>
            <form name={"deleteForm"} method={"POST"}>
                <CSRFToken csrf_token={csrf_token}></CSRFToken>
                <div>
                    <label className={"mb-3"}>Are you sure?</label>
                </div>
                <button className={"btn btn-danger me-2"} type={"submit"}><i className={"bi bi-trash"}> Delete</i>
                </button>
                <button type={"button"} className={"btn btn-outline-secondary"} onClick={() => history.back()}>
                    <i className={"bi bi-x-lg"}></i> Cancel
                </button>
            </form>
        </>
    )
}

function App({csrf_token, model}) {
    const item = model["item"]
    const title = model["title"]
    return (
        <>
            <h4>{title} :: {item.name}</h4>
            <br/>
            <DeleteView csrf_token={csrf_token} item={item}></DeleteView>
        </>
    )
}


const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText.trim()
const model = JSON.parse(model_data)
const csrf_token = document.getElementById("csrf_token").innerText.trim()

root.render(<App csrf_token={csrf_token} model={model}/>)