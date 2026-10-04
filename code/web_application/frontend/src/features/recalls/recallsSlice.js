import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { apiClient } from "../../api.js";


function errorMessage(error, fallback) {
  const detail = error.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map((item) => item.msg).join("; ");
  return error.message || fallback;
}

export const fetchRecalls = createAsyncThunk(
  "recalls/fetch",
  async ({ query = "", page = 1 } = {}, thunkApi) => {
    try {
      const params = { page, page_size: 50 };
      if (query.trim()) params.q = query.trim();
      const response = await apiClient.get("/recalls", { params });
      return response.data;
    } catch (error) {
      return thunkApi.rejectWithValue(errorMessage(error, "Unable to load recalls"));
    }
  },
);

export const createRecall = createAsyncThunk(
  "recalls/create",
  async (payload, thunkApi) => {
    try {
      const response = await apiClient.post("/recalls", payload);
      return response.data;
    } catch (error) {
      return thunkApi.rejectWithValue(errorMessage(error, "Unable to create recall"));
    }
  },
);

export const updateRecall = createAsyncThunk(
  "recalls/update",
  async ({ id, payload }, thunkApi) => {
    try {
      const response = await apiClient.put(`/recalls/${id}`, payload);
      return response.data;
    } catch (error) {
      return thunkApi.rejectWithValue(errorMessage(error, "Unable to update recall"));
    }
  },
);

export const deleteRecall = createAsyncThunk(
  "recalls/delete",
  async (id, thunkApi) => {
    try {
      await apiClient.delete(`/recalls/${id}`);
      return id;
    } catch (error) {
      return thunkApi.rejectWithValue(errorMessage(error, "Unable to delete recall"));
    }
  },
);

const recallsSlice = createSlice({
  name: "recalls",
  initialState: {
    items: [], page: 1, pageSize: 50, total: 0,
    loading: false, error: null, notice: null,
  },
  reducers: {
    clearRecallNotice(state) {
      state.notice = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchRecalls.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchRecalls.fulfilled, (state, action) => {
        state.loading = false;
        state.items = action.payload.records;
        state.page = action.payload.page;
        state.pageSize = action.payload.page_size;
        state.total = action.payload.total;
      })
      .addCase(fetchRecalls.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      .addCase(createRecall.fulfilled, (state, action) => {
        state.items.push(action.payload);
        state.notice = `Added recall ${action.payload.recall_code} successfully.`;
      })
      .addCase(createRecall.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(updateRecall.fulfilled, (state, action) => {
        const index = state.items.findIndex((item) => item.id === action.payload.id);
        if (index >= 0) state.items[index] = action.payload;
        state.notice = `Updated recall ${action.payload.recall_code} successfully.`;
      })
      .addCase(updateRecall.rejected, (state, action) => {
        state.error = action.payload;
      })
      .addCase(deleteRecall.fulfilled, (state, action) => {
        state.items = state.items.filter((item) => item.id !== action.payload);
        state.notice = `Deleted recall ID ${action.payload} successfully.`;
      })
      .addCase(deleteRecall.rejected, (state, action) => {
        state.error = action.payload;
      });
  },
});

export const { clearRecallNotice } = recallsSlice.actions;
export default recallsSlice.reducer;
