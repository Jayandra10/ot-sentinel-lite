(**
  OT Sentinel Lite - baseline conveyor POU skeleton
  Lab use only. No physical I/O or safety function is assumed.
*)
VAR
    Start_PB    : BOOL;
    Stop_PB     : BOOL;
    Photoeye    : BOOL;
    Jam_Sensor  : BOOL;

    Conveyor_Run : BOOL;
    Fault_Lamp   : BOOL;
    Item_Count   : DINT;
    Jam_Timeout  : TIME := T#5s;
    Line_State   : INT;

    PE_Rise  : R_TRIG;
    JamTimer : TON;
END_VAR

(* Stop has priority over Start. *)
IF Stop_PB THEN
    Conveyor_Run := FALSE;
ELSIF Start_PB THEN
    Conveyor_Run := TRUE;
END_IF;

PE_Rise(CLK := Photoeye);
IF Conveyor_Run AND PE_Rise.Q THEN
    Item_Count := Item_Count + 1;
END_IF;

JamTimer(IN := Conveyor_Run AND Jam_Sensor, PT := Jam_Timeout);
Fault_Lamp := JamTimer.Q;
Line_State := SEL(Fault_Lamp, 1, 2);  (* 1 = RUN, 2 = FAULT *)

