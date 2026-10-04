import { configureStore } from "@reduxjs/toolkit";

import recallsReducer from "./features/recalls/recallsSlice.js";


export const store = configureStore({
  reducer: {
    recalls: recallsReducer,
  },
});
