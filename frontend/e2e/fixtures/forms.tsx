import React from 'react';
import { createRoot } from 'react-dom/client';
import '../../src/lib/i18n';
import { CreateRFQModal } from '../../src/components/rfq/CreateRFQModal';
import { LineItemEditDialog } from '../../src/components/review/LineItemEditDialog';
import { LineItemAddDialog } from '../../src/components/review/LineItemAddDialog';
const capture = (value: unknown) => { (window as any).saved = value; return Promise.resolve(); };
const close = () => {};
const kind = new URLSearchParams(location.search).get('kind');
const item = { id: '1', description_raw: 'Valve', quantity: '2.5', unit: 'pcs', unit_price: '10.25', total_price: '25.625', lead_time_days: '0', currency: 'USD' };
createRoot(document.getElementById('root')!).render(kind === 'edit'
  ? <LineItemEditDialog isOpen item={item as any} rfqLineItems={[]} onClose={close} onSave={(id, patch, reason) => capture({id, patch, reason})}/>
  : kind === 'add' ? <LineItemAddDialog isOpen currency="USD" rfqLineItems={[]} onClose={close} onAdd={capture}/>
  : <CreateRFQModal isOpen onClose={close} onSuccess={close}/>);
