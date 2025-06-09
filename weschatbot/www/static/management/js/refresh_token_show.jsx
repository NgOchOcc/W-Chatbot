import {createRoot} from "react-dom/client";
import React from "react";

const container = document.getElementById("root_container")
const root = createRoot(container)
const model_data = document.getElementById("model").innerText
const model = JSON.parse(model_data)

function App({model}) {
    return (
        <>
            <div className={"col-md-6"}>
                <form>
                    <div className="form-group">
                        <label htmlFor="expiresAtInput"><strong>Expires at</strong></label>
                        <input readOnly={true} type="text" value={model["expires_at"]} className="form-control"
                               id="expiresAtInput"/>
                    </div>
                    <br/>
                    <div className="form-group">
                        <label htmlFor="refreshTokenTextArea"><strong>Refresh Token</strong></label>
                        <textarea className="form-control" id="refreshTokenTextArea"
                                  rows="7">{model["refresh_token"]}</textarea>
                    </div>
                </form>
                <br/>
                <p>Please copy the refresh token, you will not see it again!</p>
            </div>
        </>
    )
}

root.render(<App model={model}/>)
