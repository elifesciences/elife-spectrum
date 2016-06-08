%% Diffusion Model
%% Cellular Automata model for growth of yeast communities

% This code is free to use for any purposes, provided any publications resulting from the use of this code reference the original code/author.
% Author:  Babak Momeni (bmomeni@gmail.com)
% Date:    11/2012
% The code is not guaranteed to be free of errors. Please notify the author of any bugs, and contribute any modifications or bug fixes back to the original author.

% Diffusion in 3D; diffusion inside the community slower than agarose
% 3D diffusion for transfer of nutrients
% nonhomogeneous media
% space occupied by dead cells
% FCU: fast uptake
% CI: confinement independent
% ES2: Expansion to sides, bud to top or sides when confined
% EB: Boundary condition (continuous flow) explicitly applied at the agar-community interface
% EBP: Periodic boundary condition on the sides (in addition to EB)

clear
rand('twister',5489)

rt1 = 1; % initial ratio of population #1
rt2 = 100; % initial ratio of population #2
savename = strcat('CA3DCOMP_FCU_CI_ES2_EBP_c5g15d60_37_37_N10000_',num2str(rt1),'_',num2str(rt2),'_t48_vm5_dt1_5s_rg5_Nc120Naz400_S2e8_D0_360_D1_20');

%% Parameters
r1 = 0.37; % max reproduction rate, per hour
r2 = 0.37; % max reproduction rate, per hour
d1 = 0.015; % death rate, per hour
d2 = 0.015; % death rate, per hour
alpha1 = 1; % fmole per cell consumed to make a new cell type 1
alpha2 = 1; % fmole per cell consumed to make a new cell type 2
K1 = 1e6; % Monod constant; fmole/ml
K2 = 1e6; % Monod constant; fmole/ml

vm1 = 5; % maximum uptake rate, fmole/hour
vm2 = 5; % maximum uptake rate, fmole/hour

T1 = log(2)/r1; % minimum division time
T2 = log(2)/r2; % minimum division time

T1m = alpha1/vm1; % minimum nutrition acquiring time
Kmm1 = T1/T1m * K1; % Michaelis-Menten constant
T2m = alpha2/vm2; % minimum nutrition acquiring time
Kmm2 = T2/T2m * K2; % Michaelis-Menten constant
%vm1 = r1*alpha1/log(2); % maximum uptake rate, fmole/hour
%vm2 = r2*alpha2/log(2); % maximum uptake rate, fmole/hour
%Kmm1 = K1; % Michaelis-Menten constant
%Kmm2 = K2; % Michaelis-Menten constant

D0 = 360; % diffusion constant in agarose/agar, microns2/s
D1 = 20; % diffusion constant in cells, microns2/s

%% Definition of solution domain
% Length scale
c = 5; % grid size for cells, microns
SC = 3; % ratio of community diffusion grid size to cell grid size
SD = 4; % ratio of agar diffusion grid size to community diffusion grid size
g = SC*c; % grid size for diffusion in communities, microns
d = SD*g; % grid size for diffusion in agar, microns
dV = c^3 * 1e-12; % volume of each grid cube for cwll, ml
dVc = g^3 * 1e-12; % volume of each grid cube for diffusion in community, ml
dVa = d^3 * 1e-12; % volume of each grid cube for diffusion in agar, ml
h = 0.5*(g+d); % grid size at the interface between the comm and agar grids

rg0 = 5; % neghborhood radius for expansion to sides

%% Diffusion simulation domain
Na = 10; % total number of agar grids to be simulated in x-y, each at size d
Naz = 400; % total number of agar grids to be simulated in z, each at size d
Nd = Na*SD; % total number of comm grids to be simulated in x-y, each at size g
Ndz = 20; % total number of comm grids to be simulated in z, each at size g

%% Cell simulation domain
Nc = Nd*SC; % total number of cell grids to be simulated in x-y
Nz = Ndz*SC; % total number of cell grids to be simulated in z

S0 = 2e8; %initial conc of limiting nutrient in agar, in fmole/ml
Sa = S0*ones(Na,Na,Naz); %concentration of nutrient in agar grids
Sd = zeros(Nd,Nd,Ndz); %concentration of nutrient in community diffusion grid
Sde = zeros(Nc,Nc,Nz);%concentration of nutrient in cell grid
Dd = zeros(Nd,Nd,Ndz); %diffusion constant in community diffusion grid, to be changed when cells occupy part or all of grid
Sb = 0.5*S0*ones(Nd,Nd); % concentration at the boundary of agar and community; 0.5 or 1 or 0 makes no difference

[xxd,yyd] = meshgrid((SD+1)/2:Nd+(SD-1)/2,(SD+1)/2:Nd+(SD-1)/2);

%% Initial cell distrbution
NT0 = 10000; % initial total cell surface density, 1/mm2
N1 = round(NT0*rt1/(rt1+rt2)*c*Nc*c*Nc/1e6); % initial number of type 1 cells, (R)
N2 = round(NT0*rt2/(rt1+rt2)*c*Nc*c*Nc/1e6); % initial number of type 2 cells, (Y)
X = zeros(Nc,Nc,Nz); % 3D array containing cells; 0 (empty space), 1 (type 1, live), 0.5 (type 1, dead), 2 (type 2, live), 1.5 (type 2, dead)
U = zeros(Nc,Nc,Nz); % 3D array containing amount of nutrient accumulated in each cell (in fmole)
T = zeros(Nc,Nc,Nz); % 3D array containing the last division time for each cell
NB = zeros(Nc,Nc,Nz); % Number of budding events at each location
nn = 0; %counter for the following loop of initializing the system
while nn < N1,
    i = floor(Nc*rand(1))+1;
    j = floor(Nc*rand(1))+1;
    k = 1;
    if X(i,j,k) == 0;
        nn = nn+1;
        X(i,j,k) = 1;
        T(i,j,k) = -rand(1)*T1;  %to account for the asynchronous nature of cells - how long ago the division before t=0 happened
        U(i,j,k) = rand(1)*alpha1; %to account for the asynchronous nature of cells - how much nutrient accumulated up to t=0
    end
end
nn = 0;
while nn < N2,
    i = floor(Nc*rand(1))+1;
    j = floor(Nc*rand(1))+1;
    k = 1;
    if X(i,j,k) == 0;
        nn = nn+1;
        X(i,j,k) = 2;
        T(i,j,k) = -rand(1)*T2;
        U(i,j,k) = rand(1)*alpha2;
    end
end

%% Cell-growth time-course
tau0 = 0; % initial time in hours
tauf = 48; % final time of simulation in hours
dtau = 0.1; % in hours, cell growth update
ts = 2; % in hours, sampling time for snapshots of sections
r1e = r1*dtau; % probability of reproduction in a time step
d1e = d1*dtau; % probability of death in a time step
r2e = r2*dtau; % probability of reproduction in a time step
d2e = d2*dtau; % probability of death in a time step

taurng = tau0:dtau:tauf;

X1lm = zeros(size(taurng)); %number of live type 1 cells at different time points
X2lm = zeros(size(taurng)); %number of live type 2 cells at different time points
X1m = zeros(size(taurng)); %number of total type 1 cells at different time points
X2m = zeros(size(taurng)); %number of total type 2 cells at different time points

%debugging parameters
SPa = zeros(Naz,length(taurng)); %x-y average conc in agar along z over time
SPd = zeros(Ndz,length(taurng)); %x-y average conc in community along z over time
UAcc1 = zeros(size(taurng)); % Accumulated nutrients in live cells
UAcc2 = zeros(size(taurng)); % Accumulated nutrients in live cells
UW1 = zeros(size(taurng)); % Wasted nutrients in dead cells
UW2 = zeros(size(taurng)); % Wasted nutrients in dead cells
SAccA = zeros(size(taurng)); % Total nutrients in the agar region
SAccC = zeros(size(taurng)); % Total nutrients in the cell region

ct = 0; % counter for time points
cS = 0; % counter for sectioning

Q = [1 0; -1 0; 0 1; 0 -1; 1 -1; -1 1; 1 1; -1 -1]; % locations of eight neighbor grids
Qc = [1 0; -1 0; 0 1; 0 -1]; % locations of bud for confined cells

for tau = taurng,
    ct = ct+1;
    tic
    %     disp([mean(mean(Sa(:,:,Naz))) mean(mean(Sd(:,:,1)))])
    %     pause

%     figure(17)
%     imagesc(sum((X>0.25).*(X<1.25),3))
%     axis image
%     colormap([0 0 0; 0.1 0 0; 0.2 0 0; 0.3 0 0; 0.4 0 0; 0.5 0 0; 0.6 0 0; 0.7 0 0; 0.8 0 0; 0.9 0 0; 1 0 0])
%     figure(18)
%     imagesc(sum((X>1.25).*(X<2.25),3))
%     axis image
%     colormap([0 0 0; 0 0.1 0; 0 0.2 0; 0 0.3 0; 0 0.4 0; 0 0.5 0; 0 0.6 0; 0 0.7 0; 0 0.8 0; 0 0.9 0; 0 1 0])

    % Update cell activity
    [zm,zi] = sort(rand(1,Nz-1)); % random order for cells at different heights
    for z = zi,
        zd = floor((z-1)/SC)+1;
        [I,J] = find((X(:,:,z)==1)+(X(:,:,z)==2)); % find all live cells at height z
        Ncc = length(I);
        [SS,OS] = sort(rand(1,Ncc));
        I = I(OS);
        J = J(OS);
        for cc = 1:Ncc;

            Id = floor((I(cc)-1)/SC)+1; % diffusion index along I
            Jd = floor((J(cc)-1)/SC)+1; % diffusion index along J
            xd = I(cc); % location of cell along x
            yd = J(cc); % location of cell along y

            live = 1;
            % Is the cell dead?
            cd = rand(1);
            if (X(xd,yd,z) == 1)&&(cd < d1e),
                X(xd,yd,z) = 0.5;
                live = 0;
            end
            if (X(xd,yd,z) == 2)&&(cd < d2e),
                X(xd,yd,z) = 1.5;
                live = 0;
            end

            % Cell division and rearrangement
            if (X(xd,yd,z) == 1),
                Ti = T1;
                alpha = alpha1;
            end
            if (X(xd,yd,z) == 2),
                Ti = T2;
                alpha = alpha2;
            end

            if (live==1)&&(tau-T(xd,yd,z) >= Ti)&&(U(xd,yd,z) >= alpha),
                Budded = 0;
                Natt = 0;
                [qm1,qi1] = sort(rand(1,4)); % random index for neighboring grids
                [qm2,qi2] = sort(rand(1,4)); % random index for neighboring grids
                qi = [qi1 4+qi2];
                while (Budded==0)&&(Natt<8), % try immediate neighboring grids
                    Natt = Natt+1;
                    xb = I(cc) + Q(qi(Natt),1);
                    if xb > Nc, xb = xb-Nc; end
                    if xb < 1, xb = xb+Nc; end
                    yb = J(cc) + Q(qi(Natt),2);
                    if yb > Nc, yb = yb-Nc; end
                    if yb < 1, yb = yb+Nc; end

                    if X(xb,yb,z)==0, % if available space, bud into it
                        zb = z;
                        while (zb>=2)&&(X(xb,yb,zb-1)==0),
                            zb = zb-1;
                        end
                        U(xd,yd,z) = U(xd,yd,z)-alpha;
                        Budded = 1;
                        X(xb,yb,zb) = X(xd,yd,z);
                        T(xb,yb,zb) = tau;
                        NB(xd,yd,z) = NB(xd,yd,z)+1;
                        U(xb,yb,zb) = 0;
                        T(xd,yd,z) = tau;
                    end
                end
                if (Budded==0), % try extended neighborhood in the same plane
                    rg = rg0;
                    xdp = xd;
                    ydp = yd;
                    if xd+rg > Nc,
                        Xp = [X(:,:,z); X(1:xd+rg-Nc,:,z)];  % extend along +x; size(Xp)=xd+rg
                    else
                        if xd-rg < 1,
                            Xp = [X(Nc+xd-rg:Nc,:,z); X(:,:,z)]; % extend along -x; size(Xp)=Nc-xd+rg+1
                            xdp = rg+1;
                        else
                            Xp = X(:,:,z);
                        end
                    end
                    if yd+rg > Nc,
                        Xp = [Xp, Xp(:,1:yd+rg-Nc)];
                    else
                        if yd-rg < 1,
                            Xp = [Xp(:,Nc+yd-rg:Nc), Xp];
                            ydp = rg+1;
                        end
                    end
                    Ng = Xp(xdp-rg:xdp+rg,ydp-rg:ydp+rg);
                    if sum(sum(Ng>0.25))<(2*rg+1)^2,
                        [Ie,Je] = find(Ng==0);
                        [SSe,OSe] = min(sqrt((Ie-rg-1).^2+(Je-rg-1).^2));
                        if SSe <= rg,
                            xe = Ie(OSe);
                            ye = Je(OSe);
                            TP = TracePath(rg+1,rg+1,xe,ye);
                            NT = size(TP,1);
                            TP(:,1) = TP(:,1) + xd-rg-1;
                            TP(:,1) = TP(:,1) + Nc*((TP(:,1)<1)-(TP(:,1)>Nc));
                            TP(:,2) = TP(:,2) + yd-rg-1;
                            TP(:,2) = TP(:,2) + Nc*((TP(:,2)<1)-(TP(:,2)>Nc));
                            zb = z;
                            while (zb>=2)&&(X(TP(NT,1),TP(NT,2),zb-1)==0),
                                zb = zb-1;
                            end
                            X(TP(NT,1),TP(NT,2),zb) = X(TP(NT-1,1),TP(NT-1,2),z);
                            U(TP(NT,1),TP(NT,2),zb) = U(TP(NT-1,1),TP(NT-1,2),z);
                            T(TP(NT,1),TP(NT,2),zb) = T(TP(NT-1,1),TP(NT-1,2),z);
                            for ctr = NT-1:-1:2,
                                X(TP(ctr,1),TP(ctr,2),z) = X(TP(ctr-1,1),TP(ctr-1,2),z);
                                U(TP(ctr,1),TP(ctr,2),z) = U(TP(ctr-1,1),TP(ctr-1,2),z);
                                T(TP(ctr,1),TP(ctr,2),z) = T(TP(ctr-1,1),TP(ctr-1,2),z);
                            end
                            X(TP(1,1),TP(1,2),z) = X(xd,yd,z);
                            U(TP(1,1),TP(1,2),z) = 0;
                            T(TP(1,1),TP(1,2),z) = tau;
                            Budded = 1;
                        end
                    end
                end
                if (Budded == 0), % bud to top or sides and push cells above
                    cq = rand(1);
                    if cq < 0.7,
                        U(xd,yd,z) = U(xd,yd,z)-alpha;
                        T(xd,yd,z) = tau;
                        X(xd,yd,z+1:Nz) = X(xd,yd,z:Nz-1);
                        U(xd,yd,z+1:Nz) = U(xd,yd,z:Nz-1);
                        T(xd,yd,z+1:Nz) = T(xd,yd,z:Nz-1);
                    else
                        U(xd,yd,z) = U(xd,yd,z)-alpha;
                        T(xd,yd,z) = tau;
                        [qm3,qi3] = sort(rand(1,4)); % random index for neighboring grids
                        xb = I(cc) + Qc(qi3(1),1);
                        if xb > Nc, xb = xb-Nc; end
                        if xb < 1, xb = xb+Nc; end
                        yb = J(cc) + Qc(qi3(1),2);
                        if yb > Nc, yb = yb-Nc; end
                        if yb < 1, yb = yb+Nc; end
                        X(xb,yb,z+1:Nz) = X(xb,yb,z:Nz-1);
                        U(xb,yb,z+1:Nz) = U(xb,yb,z:Nz-1);
                        T(xb,yb,z+1:Nz) = T(xb,yb,z:Nz-1);
                        X(xb,yb,z) = X(xd,yd,z);
                        T(xb,yb,z) = tau;
                        NB(xd,yd,z) = NB(xd,yd,z)+1;
                        U(xb,yb,z) = 0;
                    end
                end
            end
        end
        X1lm(z,ct) = sum(sum(X(:,:,z)==1));
        X2lm(z,ct) = sum(sum(X(:,:,z)==2));
        X1m(z,ct) = sum(sum((X(:,:,z)>0.25).*(X(:,:,z)<1.25)));
        X2m(z,ct) = sum(sum((X(:,:,z)>1.25).*(X(:,:,z)<2.25)));
    end
    UAcc1(ct) = sum(sum(sum(U.*(X==1))));
    UAcc2(ct) = sum(sum(sum(U.*(X==2))));
    UW1(ct) = sum(sum(sum(U.*(X==0.5))));
    UW2(ct) = sum(sum(sum(U.*(X==1.5))));
    SAccC(ct) = sum(sum(sum(Sd)));
    SAccA(ct) = sum(sum(sum(Sa)));
    disp([tau  sum(X1lm(:,ct)) sum(X2lm(:,ct)) sum(sum(sum(X==0.5))) sum(sum(sum(X==1.5))) sum(sum(sum(U.*(X==1)))) sum(sum(sum(U.*(X==2))))])

    % Update diffusion constant according to the grids that are filled with
    % cells at this time-step
    Dd = zeros(Nd,Nd,Ndz);
    for ii = 1:SC,
        for jj = 1:SC,
            for kk = 1:SC,
                Dd = Dd + D1/SC^3*(X(ii:SC:Nc,jj:SC:Nc,kk:SC:Nz)>0.1);
            end
        end
    end

    dt0 = min(0.15*d^2/D0,0.15*g^2/D1); % diffusion and uptake time-step, in seconds
    trng = linspace(0,3600*dtau-dt0,round(3600*dtau/dt0)); % all the updates needed in the dtau time, in seconds
    dt = trng(2)-trng(1);
    %% Diffusion loop
    for t = trng,
        % Update concentration at the boundary, Sb
        Sam = [Sa(Na,:,Naz); Sa(:,:,Naz); Sa(1,:,Naz)];
        Sam = [Sam(:,Na), Sam, Sam(:,1)];
        Sae = interp2(SD*(0:Na+1),SD*(0:Na+1),Sam,xxd,yyd,'linear');
        Sb = Sb - dt/h * (D0/d*(Sb - Sae) + 1/g*Dd(:,:,1).*(Sb - Sd(:,:,1)));

        % Diffusion in the agar region
        Sbm = zeros(Na,Na);
        for ii = 1:SD,
            for jj = 1:SD,
                Sbm = Sbm + 1/SD^2*Sb(ii:SD:Nd,jj:SD:Nd);
            end
        end
        Sab = Sa(:,:,3:Naz);
        Sab(:,:,Naz-1) = Sbm;
        dSa = dt/d^2 * D0*([Sa(Na,:,2:Naz); Sa(1:Na-1,:,2:Naz)] + [Sa(2:Na,:,2:Naz); Sa(1,:,2:Naz)] + ...
            [Sa(:,Na,2:Naz), Sa(:,1:Na-1,2:Naz)] + [Sa(:,2:Na,2:Naz), Sa(:,1,2:Naz)] + ...
            Sa(:,:,1:Naz-1) + Sab - 6*Sa(:,:,2:Naz));
        Sa(:,:,2:Naz) = Sa(:,:,2:Naz) + dSa;
        Sa(:,:,1) = Sa(:,:,2);

        % Diffusion in the community region
        Sdb = zeros(Nd,Nd,Ndz-1);
        Sdb(:,:,1) = Sb;
        Sdb(:,:,2:Ndz-1) = Sd(:,:,1:Ndz-2);
        dSd = dt/g^2 * Dd(:,:,1:Ndz-1).*([Sd(Nd,:,1:Ndz-1); Sd(1:Nd-1,:,1:Ndz-1)] + ...
            [Sd(2:Nd,:,1:Ndz-1); Sd(1,:,1:Ndz-1)] + [Sd(:,Nd,1:Ndz-1), Sd(:,1:Nd-1,1:Ndz-1)] + ...
            [Sd(:,2:Nd,1:Ndz-1), Sd(:,1,1:Ndz-1)] + Sdb + Sd(:,:,2:Ndz) - 6*Sd(:,:,1:Ndz-1)) + dt/g^2 * (...
            ([Dd(2:Nd,:,1:Ndz-1); Dd(1,:,1:Ndz-1)]-Dd(:,:,1:Ndz-1)).*([Sd(2:Nd,:,1:Ndz-1); Sd(1,:,1:Ndz-1)]-Sd(:,:,1:Ndz-1))+...
            ([Dd(:,2:Nd,1:Ndz-1), Dd(:,1,1:Ndz-1)]-Dd(:,:,1:Ndz-1)).*([Sd(:,2:Nd,1:Ndz-1), Sd(:,1,1:Ndz-1)]-Sd(:,:,1:Ndz-1))+...
            (Dd(:,:,2:Ndz)-Dd(:,:,1:Ndz-1)).*(Sd(:,:,2:Ndz)-Sd(:,:,1:Ndz-1)));
        Sd(:,:,1:Ndz-1) = Sd(:,:,1:Ndz-1) + dSd;
        Sd(:,:,Ndz) = Sd(:,:,Ndz-1);

        %% Uptake
        dtu = dt/3600; % in hours
        % Nutrient uptake
        for i1 = 1:3,
            for i2 = 1:3,
                for i3 = 1:3,
                    Sde(i1:SC:Nc,i2:SC:Nc,i3:SC:Nz) = Sd;
                end
            end
        end

        Uc = (dtu*vm1*Sde./(Sde+Kmm1)).*(X==1).*(U<alpha1).*(Sde>0) + (dtu*vm2*Sde./(Sde+Kmm2)).*(X==2).*(U<alpha2).*(Sde>0);
        U = U+Uc;
        Sde = Sde-1/dV*Uc;

        Sd = zeros(Nd,Nd,Ndz);
        for ii = 1:SC,
            for jj = 1:SC,
                for kk = 1:SC,
                    Sd = Sd + 1/SC^3*Sde(ii:SC:Nc,jj:SC:Nc,kk:SC:Nz);
                end
            end
        end

    end
    SPa(:,ct) = shiftdim(mean(mean(Sa,2),1));
    SPd(:,ct) = shiftdim(mean(mean(Sd,2),1));

    if mod(tau+0.03,ts)<0.1,
        cS = cS+1;
        XS1(:,:,cS) = sum((X>0.25).*(X<1.25),3);
        XS2(:,:,cS) = sum((X>1.25).*(X<2.25),3);
        ss = round(Nc/2);
        for ii = 1:Nc,
            for jj = 1:Nz,
                Sec(ii,jj,cS) = X(ss,ii,jj);
            end
        end
        save(strcat(savename,'_ts2_cs',num2str(cS)),'X','tau')
    end
    toc
end

figure
semilogy(linspace(0,tau-dtau,ct-1),sum(X1lm(:,1:ct-1)),'r')
hold on
semilogy(linspace(0,tau-dtau,ct-1),sum(X1m(:,1:ct-1)),'r--')
semilogy(linspace(0,tau-dtau,ct-1),sum(X2lm(:,1:ct-1)),'g')
semilogy(linspace(0,tau-dtau,ct-1),sum(X2m(:,1:ct-1)),'g--')
xlabel('Time (hours)')
ylabel('Population (# of cells)')
xlim([0 tau-dtau])
legend('Live R','Total R','Live Y','Total Y')

ss = 61;
for ii = 1:Nc
    for jj = 1:Nz,
        SecT(ii,jj) = X(ii,ss,jj);
    end
end
figure; imagesc((SecT')); axis image
%     colormap([0 0 0; 0.1 0 0; 0.2 0 0; 0.3 0 0; 0.4 0 0; 0.5 0 0; 0.6 0 0; 0.7 0 0; 0.8 0 0; 0.9 0 0; 1 0 0; 0 0.1 0; 0 0.2 0; 0 0.3 0; 0 0.4 0; 0 0.5 0; 0 0.6 0; 0 0.7 0; 0 0.8 0; 0 0.9 0; 0 1 0])
colormap([0 0 0; 0.1 0 0; 0.2 0 0; 0.3 0 0; 0.4 0 0; 0.5 0 0; 0.6 0 0; 0.7 0 0; 0.8 0 0; 0.9 0 0; 1 0 0; 0 0.1 0; 0 0.2 0; 0 0.3 0; 0 0.4 0; 0 0.5 0; 0 0.6 0; 0 0.7 0; 0 0.8 0; 0 0.9 0; 0 1 0])

figure
imagesc(sum((X>0.25).*(X<1.25),3))
axis image
colormap([0 0 0; 0.1 0 0; 0.2 0 0; 0.3 0 0; 0.4 0 0; 0.5 0 0; 0.6 0 0; 0.7 0 0; 0.8 0 0; 0.9 0 0; 1 0 0])
figure
imagesc(sum((X>1.25).*(X<2.25),3))
axis image
colormap([0 0 0; 0 0.1 0; 0 0.2 0; 0 0.3 0; 0 0.4 0; 0 0.5 0; 0 0.6 0; 0 0.7 0; 0 0.8 0; 0 0.9 0; 0 1 0])

save(savename) 
