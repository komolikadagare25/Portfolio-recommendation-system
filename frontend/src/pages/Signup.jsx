import React from "react";
import MarketPanel from "../components/MarketPanel";
import AuthForm from "../components/AuthForm";
import "./AuthScreen.css";


function Signup(){

return(

<div className="auth-screen">

<div className="auth-screen__card">

<MarketPanel />

<AuthForm mode="signup"/>

</div>

</div>

)

}

export default Signup;