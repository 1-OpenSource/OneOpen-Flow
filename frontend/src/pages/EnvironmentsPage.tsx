import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { environmentService } from "../services/api";

export function EnvironmentsPage() {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ["environments"], queryFn: environmentService.list });
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [variablesJson, setVariablesJson] = useState('{\n  "baseUrl": "http://localhost:3000"\n}');
  const create = useMutation({
    mutationFn: () =>
      environmentService.create({
        name,
        description,
        variables: JSON.parse(variablesJson),
      }),
    onSuccess: () => {
      setName("");
      setDescription("");
      qc.invalidateQueries({ queryKey: ["environments"] });
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
          <h1>Environments</h1>
          <p>Named variable sets for workflow runs.</p>
        </div>
      </div>
      <div className="grid-2">
        <form className="card stack" onSubmit={onSubmit}>
          <div className="form-field">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="form-field">
            <label>Description</label>
            <input value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <div className="form-field">
            <label>Variables JSON</label>
            <textarea value={variablesJson} onChange={(e) => setVariablesJson(e.target.value)} rows={8} />
          </div>
          <button className="btn btn-primary" type="submit">Create environment</button>
        </form>
        <div className="card">
          <table className="table">
            <thead>
              <tr><th>Name</th><th>Variables</th><th>Updated</th></tr>
            </thead>
            <tbody>
              {data.map((env) => (
                <tr key={env.id}>
                  <td>{env.name}</td>
                  <td><code>{Object.keys(env.variables || {}).join(", ") || "—"}</code></td>
                  <td>{new Date(env.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
