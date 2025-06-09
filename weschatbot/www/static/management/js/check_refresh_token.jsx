import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {CSRFToken} from "./utils";

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)
const csrf_token = document.getElementById("csrf_token").innerText.trim()

function Result({model}) {
    return (
        <>
            <div className={"container-fluid"}>
                <table className="table table-hover">
                    <tbody>
                    {
                        Object.entries(model).map(([k, v]) => {
                            return (
                                <tr>
                                    <td>{k}</td>
                                    <td>{v}</td>
                                </tr>
                            )
                        })
                    }
                    </tbody>
                </table>
            </div>
        </>
    )
}

function App({model, csrf_token}) {
    const [result, setResult] = useState({})
    const [refresh_token, setRefresh_token] = useState("")

    const onSubmitCheckRefreshToken = (event) => {
        event.preventDefault()
        const formData = new FormData()
        formData.append("csrf_token", csrf_token)
        formData.append("refresh_token", refresh_token)

        fetch("/admin/ViewModelRefreshToken/check_refresh_token", {
            method: "POST",
            body: formData,
        }).then(res => res.json())
            .then(res => setResult(res["payload"]))
            .catch(err => console.log(err))
    }

    return (
        <>
            <h4>Check refresh token</h4>
            <br/>
            <div className="row">
                <div className={"col-md-6"}>
                    <form onSubmit={onSubmitCheckRefreshToken}>
                        <CSRFToken csrf_token={csrf_token}></CSRFToken>
                        <div className="form-group">
                            <label htmlFor="refreshTokenTextArea"><strong>Refresh Token</strong></label>
                            <textarea className="form-control" onChange={(e) => setRefresh_token(e.target.value)}
                                      id="refreshTokenTextArea"
                                      rows="7">{refresh_token}</textarea>
                        </div>
                        <br/>
                        <button className={"btn btn-success me-1"} type={"submit"}>
                            Check
                        </button>
                    </form>

                </div>
                <div className={"col-md-6"}>
                    <strong>Result</strong>
                    <Result model={result}></Result>
                </div>
            </div>
        </>
    )
}

root.render(<App model={model} csrf_token={csrf_token}/>)
