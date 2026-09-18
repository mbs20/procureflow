import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { translateBackendError } from "../lib/errorMessageMap";
type Event = {id: string; rfq_id: string; event_type: string; actor_type: string; timestamp: string};
export const AuditPage: React.FC = () => {
 const {t, i18n} = useTranslation();
 const [page, setPage] = useState(1);
 const [data, setData] = useState<{items: Event[]; total: number}>({items: [], total: 0});
 const [loading, setLoading] = useState(true);
 const [error, setError] = useState<string | null>(null);
 useEffect(() => {
  const controller = new AbortController();
  setLoading(true); setError(null);
  fetch(`${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/audit?page=${page}&page_size=25`, {signal: controller.signal})
   .then(async response => {if (!response.ok) throw new Error(`${response.status} ${response.statusText}`); return response.json();})
   .then(setData).catch(e => {if (!controller.signal.aborted) setError(translateBackendError(e, t));})
   .finally(() => {if (!controller.signal.aborted) setLoading(false);});
  return () => controller.abort();
 }, [page, t]);
 return <section className="space-y-4">
  <h1 className="text-2xl font-bold">{t('audit.title')}</h1>
  {loading ? <p role="status">{t('common.loading')}</p> : error ? <p role="alert">{error}</p> : <>
   {data.items.length === 0 ? <p>{t('audit.noEvents')}</p> : <ol className="space-y-3">{data.items.map(event =>
    <li key={event.id} className="rounded border p-3 break-words">
     <div>{event.event_type}</div>
     <time>{new Date(event.timestamp.endsWith('Z') ? event.timestamp : event.timestamp + 'Z').toLocaleString(i18n.language)}</time>
     <div><Link className="underline" to={`/rfqs/${event.rfq_id}`}>RFQ {event.rfq_id}</Link></div>
    </li>)}</ol>}
   <div className="flex gap-4"><button disabled={page === 1} onClick={() => setPage(page - 1)}>{t('audit.previous')}</button>
    <span>{page}</span><button disabled={page * 25 >= data.total} onClick={() => setPage(page + 1)}>{t('audit.next')}</button></div>
  </>}
 </section>;
};
