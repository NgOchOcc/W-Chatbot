import {createRoot} from "react-dom/client";
import React from "react";


function ShowView({items}) {
    console.log(items)
    return (
        <>
            <table className={"table table-striped table-bordered table-hover"}>
                <tbody>
                {Object.entries(items).map(([key, value]) => {
                    return <tr>
                        <td>
                            {key}
                        </td>
                        <td>
                            {value}
                        </td>
                    </tr>
                })}
                </tbody>
            </table>
        </>
    )
}


function App({model}) {
    return (
        <>
            <h4>Configurations</h4>
            <br/>
            <ShowView items={model}></ShowView>
            <button type={"button"} className={"btn btn-outline-danger"} onClick={() => history.back()}><i
                className={"bi bi-x-lg"}></i> Back
            </button>
        </>
    )
}


const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)
