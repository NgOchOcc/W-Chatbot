import React from "react";


function CSRFToken({csrf_token}) {
    return (
        <input type={"hidden"} className={"form-control"} name={"csrf_token"} value={csrf_token}></input>
    )
}

export {CSRFToken}