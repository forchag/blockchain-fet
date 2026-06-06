---- MODULE AccessControl ----
EXTENDS Naturals, FiniteSets, Sequences, TLC

CONSTANTS Users, Roles, Perms, Resources, Zones,
          u1, u2, u3, Admin, Farmer, Sensor, p1, p2, p3, p4, r1, r2, North, South

VARIABLES granted,
          pending,
          requestLog,
          roleAssignments,
          roleExpiry,
          crossZoneTokens,
          clock

Vars == << granted, pending, requestLog, roleAssignments, roleExpiry, crossZoneTokens, clock >>

Decisions == {"PENDING", "GRANT", "DENY", "REVOKE"}

ResourceZone(resource) ==
  CASE resource = r1 -> North
    [] resource = r2 -> South

Requests == {
  [ user |-> u, perm |-> p, resource |-> r, zone |-> ResourceZone(r) ] :
    u \in Users, p \in Perms, r \in Resources
}

RolePerms(role) ==
  CASE role = Admin  -> Perms
    [] role = Farmer -> {p1, p2, p3}
    [] role = Sensor -> {p1}

Assignments == [user: Users, role: Roles, zone: Zones]
Tokens == [user: Users, fromZone: Zones, toZone: Zones, expires: 0..10]
LogEntries == [req: Requests, decision: Decisions, at: 0..10]

InitialRequests == {
  [ user |-> u1, perm |-> p1, resource |-> r1, zone |-> North ],
  [ user |-> u2, perm |-> p2, resource |-> r1, zone |-> North ],
  [ user |-> u3, perm |-> p4, resource |-> r2, zone |-> South ]
}

InitialAssignments == {
  [ user |-> u1, role |-> Admin,  zone |-> North ],
  [ user |-> u1, role |-> Admin,  zone |-> South ],
  [ user |-> u2, role |-> Farmer, zone |-> North ],
  [ user |-> u3, role |-> Sensor, zone |-> South ]
}

CandidateAssignments == InitialAssignments \cup {
  [ user |-> u2, role |-> Farmer, zone |-> South ],
  [ user |-> u3, role |-> Sensor, zone |-> North ]
}

CandidateTokens == {
  [ user |-> u2, fromZone |-> North, toZone |-> South, expires |-> 5 ],
  [ user |-> u3, fromZone |-> South, toZone |-> North, expires |-> 5 ],
  [ user |-> u1, fromZone |-> North, toZone |-> South, expires |-> 10 ]
}

ActiveRoleAt(t, assignments, expiry, user, perm, zone) ==
  \E assignment \in assignments :
    /\ assignment.user = user
    /\ assignment.zone = zone
    /\ perm \in RolePerms(assignment.role)
    /\ expiry[assignment] >= t

ActiveTokenAt(t, tokens, user, fromZone, toZone) ==
  \E token \in tokens :
    /\ token.user = user
    /\ token.fromZone = fromZone
    /\ token.toZone = toZone
    /\ token.expires >= t

AuthorizedAt(t, assignments, expiry, tokens, req) ==
  \/ ActiveRoleAt(t, assignments, expiry, req.user, req.perm, req.zone)
  \/ \E assignment \in assignments :
       /\ assignment.user = req.user
       /\ assignment.zone # req.zone
       /\ req.perm \in RolePerms(assignment.role)
       /\ expiry[assignment] >= t
       /\ ActiveTokenAt(t, tokens, req.user, assignment.zone, req.zone)

LoggedRequests == {entry.req : entry \in requestLog}

NoUnauthorizedAccess ==
  \A req \in granted : AuthorizedAt(clock, roleAssignments, roleExpiry, crossZoneTokens, req)

AllRequestsLogged ==
  pending \cup granted \subseteq LoggedRequests

SafeGrantsAt(t, assignments, expiry, tokens, grants) ==
  { req \in grants : AuthorizedAt(t, assignments, expiry, tokens, req) }

Init ==
  /\ clock = 0
  /\ granted = {}
  /\ pending = InitialRequests
  /\ requestLog = { [ req |-> req, decision |-> "PENDING", at |-> 0 ] : req \in InitialRequests }
  /\ roleAssignments = InitialAssignments
  /\ roleExpiry = [assignment \in Assignments |-> IF assignment \in InitialAssignments THEN 10 ELSE 0]
  /\ crossZoneTokens = {}

GrantRequest ==
  \E req \in pending :
    /\ AuthorizedAt(clock, roleAssignments, roleExpiry, crossZoneTokens, req)
    /\ granted' = granted \cup {req}
    /\ pending' = pending \ {req}
    /\ requestLog' = requestLog \cup { [req |-> req, decision |-> "GRANT", at |-> clock] }
    /\ UNCHANGED <<roleAssignments, roleExpiry, crossZoneTokens, clock>>

DenyRequest ==
  \E req \in pending :
    /\ pending' = pending \ {req}
    /\ requestLog' = requestLog \cup { [req |-> req, decision |-> "DENY", at |-> clock] }
    /\ UNCHANGED <<granted, roleAssignments, roleExpiry, crossZoneTokens, clock>>

AssignRole ==
  \E assignment \in CandidateAssignments \ roleAssignments :
  \E expiry \in (clock + 1)..10 :
    /\ roleAssignments' = roleAssignments \cup {assignment}
    /\ roleExpiry' = [roleExpiry EXCEPT ![assignment] = expiry]
    /\ granted' = granted
    /\ UNCHANGED <<pending, requestLog, crossZoneTokens, clock>>

RevokeRole ==
  \E assignment \in roleAssignments :
    LET newAssignments == roleAssignments \ {assignment}
        newGrants == SafeGrantsAt(clock, newAssignments, roleExpiry, crossZoneTokens, granted) IN
    /\ roleAssignments' = newAssignments
    /\ granted' = newGrants
    /\ requestLog' = requestLog \cup { [req |-> req, decision |-> "REVOKE", at |-> clock] : req \in granted \ newGrants }
    /\ UNCHANGED <<pending, roleExpiry, crossZoneTokens, clock>>

IssueCrossZoneToken ==
  \E token \in CandidateTokens \ crossZoneTokens :
    /\ token.fromZone # token.toZone
    /\ token.expires > clock
    /\ crossZoneTokens' = crossZoneTokens \cup {token}
    /\ UNCHANGED <<granted, pending, requestLog, roleAssignments, roleExpiry, clock>>

RevokeCrossZoneToken ==
  \E token \in crossZoneTokens :
    LET newTokens == crossZoneTokens \ {token}
        newGrants == SafeGrantsAt(clock, roleAssignments, roleExpiry, newTokens, granted) IN
    /\ crossZoneTokens' = newTokens
    /\ granted' = newGrants
    /\ requestLog' = requestLog \cup { [req |-> req, decision |-> "REVOKE", at |-> clock] : req \in granted \ newGrants }
    /\ UNCHANGED <<pending, roleAssignments, roleExpiry, clock>>

Tick ==
  /\ clock < 10
  /\ LET newClock == clock + 1
         newAssignments == {assignment \in roleAssignments : roleExpiry[assignment] >= newClock}
         newTokens == {token \in crossZoneTokens : token.expires >= newClock}
         newGrants == SafeGrantsAt(newClock, newAssignments, roleExpiry, newTokens, granted) IN
       /\ clock' = newClock
       /\ roleAssignments' = newAssignments
       /\ crossZoneTokens' = newTokens
       /\ granted' = newGrants
       /\ requestLog' = requestLog \cup { [req |-> req, decision |-> "REVOKE", at |-> newClock] : req \in granted \ newGrants }
  /\ UNCHANGED <<pending, roleExpiry>>

ExpireRole ==
  \E assignment \in roleAssignments :
    /\ roleExpiry[assignment] < clock
    /\ LET newAssignments == roleAssignments \ {assignment}
           newGrants == SafeGrantsAt(clock, newAssignments, roleExpiry, crossZoneTokens, granted) IN
         /\ roleAssignments' = newAssignments
         /\ granted' = newGrants
         /\ requestLog' = requestLog \cup { [req |-> req, decision |-> "REVOKE", at |-> clock] : req \in granted \ newGrants }
    /\ UNCHANGED <<pending, roleExpiry, crossZoneTokens, clock>>

ProcessRequest == GrantRequest \/ DenyRequest

Quiesce ==
  /\ clock = 10
  /\ pending = {}
  /\ UNCHANGED Vars

Next ==
  \/ GrantRequest
  \/ DenyRequest
  \/ AssignRole
  \/ RevokeRole
  \/ IssueCrossZoneToken
  \/ RevokeCrossZoneToken
  \/ Tick
  \/ ExpireRole
  \/ Quiesce

Spec == Init /\ [][Next]_Vars /\ WF_Vars(ProcessRequest)

Liveness == \A req \in InitialRequests : req \in pending ~> req \notin pending

StateConstraint == clock <= 10

====
