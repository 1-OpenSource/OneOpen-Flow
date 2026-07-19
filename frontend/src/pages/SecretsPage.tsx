import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { secretService } from "../services/api";

export function SecretsPage() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["secrets"], queryFn: secretService.list });
  const [name, setName] = useState("");
  const [value, setValue] = useState("");
  const [description, setDescription] = useState("");
  const create = useMutation({
    mutationFn: () => secretService.create({ name, value, description }),
    onSuccess: () => {
      setName("");
      setValue("");
      setDescription("");
      qc.invalidateQueries({ queryKey: ["secrets"] });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1>Secrets</h1>
          <p>Encrypted at rest. Values are never returned after creation.</p>
        </div>
      </div>
      <div className="grid-2">
        <form className="card stack" onSubmit={onSubmit}>
          <div className="form-field">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required placeholder="LOGIN_PASSWORD" />
          </div>
          <div className="form-field">
            <label>Value</label>
            <input type="password" value={value} onChange={(e) => setValue(e.target.value)} required />
          </div>
          <div className="form-field">
            <label>Description</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <button className="btn btn-primary" type="submit">Store secret</button>
        </form>
        <div className="card">
          <table className="table">
            <thead>
              <tr><th>Name</th><th>Description</th><th>Updated</th><th></th></tr>
            </thead>
            <tbody>
              {data.map((secret) => (
                <tr key={secret.id}>
                  <td>{secret.name}</td>
                  <td className="muted">{secret.description || "—"}</td>
                  <td>{new Date(secret.updated_at).toLocaleString()}</td>
                  <td>
                    <button
                      className="btn btn-danger"
                      onClick={() => secretService.remove(secret.id).then(() => qc.invalidateQueries({ queryKey: ["secrets"] }))}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
