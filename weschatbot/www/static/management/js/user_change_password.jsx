import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {CSRFToken} from "./utils";

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)
const csrf_token = document.getElementById("csrf_token").innerText.trim()

function App({model, csrf_token}) {
    console.log(model)

    const [password, setPassword] = useState()
    const [retypePassword, setRetypePassword] = useState()

    const onSubmit = (e) => {
        if (password === retypePassword) {
            fetch(model.submit_url, {
                method: "POST",
                headers: {
                    'Content-Type': 'application/json',
                    'credentials': 'include',
                    'X-CSRFToken': csrf_token
                },
                body: JSON.stringify({
                    password: password
                })
            }).then(res => {
                if (res.status === 200) {
                    history.back()
                    alert("Password changed successfully")
                } else {
                    alert("Password changed failed")
                }
            })
        } else {
            alert("Password and confirm password do not match")
        }
    }

    return (
        <>
            <div className={"col-md-6"}>
                <h4>Change password for user: {model.user.name}</h4>
                <form onSubmit={(e) => onSubmit(e)} method="POST">
                    <CSRFToken csrf_token={csrf_token}></CSRFToken>
                    <label htmlFor="inputPassword" className="form-label">Password</label>
                    <input type="password" id="inputPassword" className="form-control"
                           aria-describedby="passwordHelpBlock" value={password} onChange={(e) => setPassword(e.target.value)}/>
                    <label htmlFor="inputRetypePassword" className="form-label">Retype Password</label>
                    <input type="password" id="inputRetypePassword" className="form-control"
                           aria-describedby="retypepasswordHelpBlock" value={retypePassword} onChange={(e) => setRetypePassword(e.target.value)}/>
                    <br/>
                    <button className={"btn btn-primary me-2"}><i
                        className="bi bi-save"></i> Save
                    </button>
                    <button type={"button"} className={"btn btn-outline-secondary"} onClick={() => {
                        history.back()
                    }}><i className="bi bi-x-lg"></i> Cancel
                    </button>
                </form>

            </div>
        </>
    )
}

root.render(<App model={model} csrf_token={csrf_token}/>)
