require("dotenv").config();
const express = require("express");
const mongoose = require("mongoose");
const PORT = process.env.PORT || 3002;
const dbUrl = process.env.MONGO_URL;
const app = express();


main().then(() => {
    console.log("Database Connected");
}).catch((err) => {
    console.log(err);
});
async function main() {
    await mongoose.connect(dbUrl);
};
app.listen(PORT, () =>{
    console.log("app is running on port 3002");
});

