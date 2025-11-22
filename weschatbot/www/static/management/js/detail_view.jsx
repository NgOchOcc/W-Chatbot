import {createRoot} from "react-dom/client";
import React from "react";

import {
    CFormTextarea,
    CFormCheck,
} from '@coreui/react';

function Actions({actions}) {
    return (
        <div className="dropdown">
            <button key={"button_actions"} className="btn btn-secondary dropdown-toggle" type="button"
                    data-bs-toggle="dropdown"
                    aria-expanded="false">
                Actions
            </button>
            <ul key={"ul_actions"} className="dropdown-menu">
                {
                    Object.entries(actions).map((item, index) => (<>
                        <li key={"li_" + index}><a key={"li_" + index} className="dropdown-item"
                                                   href={item[1]}>{item[0]}</a></li>
                    </>))
                }
            </ul>
        </div>
    )
}

function BooleanHelper({field_value}) {
    return (
        <CFormCheck
            type="checkbox"
            label={field_value ? 'Yes' : 'No'}
            checked={field_value}
            disabled
        />
    )
}

function TextHelper({field_value}) {
    return (
        <>
            {field_value && field_value.length > 200 ? (
                <CFormTextarea
                    disabled
                    rows={5}
                    value={field_value}
                />
            ) : (
                field_value
            )}
        </>
    );
}

function FieldHelper({field_value}) {
    const field_type = typeof field_value;

    switch (field_type) {
        case 'boolean':
            return <BooleanHelper field_value={field_value}></BooleanHelper>
        default:
            return <TextHelper field_value={field_value}/>
    }
}

function ShowView({detail_fields, item}) {

    console.log(detail_fields)
    console.log(item)

    return (
        <>
            <table className={"table table-striped table-bordered table-hover"}>
                <tbody>
                {detail_fields.map((field) => {
                    return <tr>
                        <td>
                            <strong>{field}</strong>
                        </td>
                        <td>
                            {/*{*/}
                            {/*    item[field] && item[field].length > 200 && <>*/}
                            {/*        <div className="mb-3">*/}
                            {/*            <textarea className="form-control" id="exampleFormControlTextarea1"*/}
                            {/*                      disabled={true}*/}
                            {/*                      rows="5">{item[field]}</textarea>*/}
                            {/*        </div>*/}
                            {/*    </> || item[field]*/}
                            {/*}*/}
                            <FieldHelper field_value={item[field]}></FieldHelper>
                        </td>
                    </tr>
                })}
                </tbody>
            </table>
            <button type={"button"} className={"btn btn-outline-danger"} onClick={() => history.back()}><i
                className={"bi bi-x-lg"}></i> Back
            </button>
        </>
    )
}

function App({model}) {
    const detail_fields = model["detail_fields"]
    const item = model["item"]
    return (
        <>
            {
                Object.keys(model["actions"]).length !== 0 && <>
                    <Actions actions={model["actions"]}></Actions>
                    <br/>
                </>
            }

            <ShowView item={item} detail_fields={detail_fields}></ShowView>
        </>
    )
}


const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

root.render(<App model={model}/>)
