import {createRoot} from "react-dom/client";
import React, {useState} from "react";
import {CSRFToken} from "./utils";


function App({model, csrf_token}) {

    const [password, setPassword] = useState()
    const [username, setUsername] = useState()
    const [jwtToken, ] = useState(model["jwt_token"])

    return (
        <>
            <br/>
            <h4>Get JWT for Http Executor :: {model.executor.name}</h4>
            <br/>
            <div className={"col-md-3"}>
                <form method="POST">
                    <CSRFToken csrf_token={csrf_token}></CSRFToken>
                    <div className="mb-3">
                        <label htmlFor={"inputUsername"} className={"form-label"}>User name</label>
                        <input type={"input"} id={"inputUsername"} name={"username"} className={"form-control"} value={username}
                               onChange={(e) => setUsername(e.target.value)}/>
                    </div>
                    <div className="mb-3">
                        <label htmlFor="inputPassword" className="form-label">Password</label>
                        <input type="password" name={"password"} id="inputPassword" className="form-control"
                               aria-describedby="passwordHelpBlock" value={password}
                               onChange={(e) => setPassword(e.target.value)}/>
                    </div>
                    <div className="mb-3">
                        <button className={"btn btn-primary me-2"}>Submit</button>
                    </div>
                </form>
                <div className="mb-3">
                    <label htmlFor="exampleFormControlTextarea1" className="form-label">Token</label>
                    <textarea className="form-control" id="exampleFormControlTextarea1" disabled={true} rows="10">{jwtToken}</textarea>
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
