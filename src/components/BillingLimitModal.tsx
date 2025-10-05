import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { AlertTriangle } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface TransactionLimitDetail {
  code?: string;
  message?: string;
  limit?: number;
  current_usage?: number;
  percentage_used?: number;
}

export const BillingLimitModal = () => {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState<TransactionLimitDetail | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const listener = (event: Event) => {
      const custom = event as CustomEvent<TransactionLimitDetail>;
      setDetail(custom.detail ?? null);
      setOpen(true);
    };

    window.addEventListener("billing:limit-exceeded", listener as EventListener);
    return () => {
      window.removeEventListener("billing:limit-exceeded", listener as EventListener);
    };
  }, []);

  const handleNavigate = () => {
    setOpen(false);
    navigate("/billing");
  };

  const limit = detail?.limit;
  const usage = detail?.current_usage;
  const percentage = detail?.percentage_used ?? undefined;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Limite mensal atingido</DialogTitle>
          <DialogDescription>
            Detectamos que esta loja alcançou o limite do plano atual. Escolha um tier com mais entregas para evitar bloqueios.
          </DialogDescription>
        </DialogHeader>

        <Alert variant="warning" className="mt-4">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>
            {detail?.message ?? "Recomendamos realizar o upgrade para liberar novas entregas."}
          </AlertDescription>
        </Alert>

        <div className="mt-4 space-y-2 text-sm">
          {typeof limit === "number" && (
            <div>
              <span className="font-medium">Limite atual:</span> {limit} entregas/mês
            </div>
          )}
          {typeof usage === "number" && (
            <div>
              <span className="font-medium">Usado:</span> {usage} entregas
              {typeof percentage === "number" ? ` (${percentage.toFixed(1)}%)` : null}
            </div>
          )}
        </div>

        <DialogFooter className="mt-6">
          <Button variant="outline" onClick={() => setOpen(false)}>
            Agora não
          </Button>
          <Button onClick={handleNavigate}>Ver planos</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default BillingLimitModal;
