from typing import Tuple
from app.config import get_settings


class StakingService:
    """
    Serviciu pentru calculul mizelor folosind strategia de progresie.

    Formula:
    - La WIN: Reset -> Pierdere_Cumulată = 0, următorul pariu = stake_initial
    - La LOSE: S_n = (Pierdere_Cumulată / (Cota_nouă - 1)) + stake_initial
    """

    def __init__(self):
        self.settings = get_settings()
        self.initial_stake = self.settings.bot_initial_stake
        self.max_progression_steps = self.settings.bot_max_progression_steps

    def calculate_stake(
        self,
        cumulative_loss: float,
        new_odds: float,
        progression_step: int,
        team_initial_stake: float = None  # Miză inițială per echipă (opțional)
    ) -> Tuple[float, bool]:
        """
        Calculează miza pentru următorul pariu.

        Args:
            cumulative_loss: Pierderea cumulată până acum pentru echipă
            new_odds: Cota pentru următorul meci
            progression_step: Pasul curent de progresie
            team_initial_stake: Miza inițială specifică echipei (dacă e setată)

        Returns:
            Tuple[float, bool]: (miza_calculată, stop_loss_atins)
        """
        # Folosim miza echipei dacă e setată, altfel cea globală
        initial = team_initial_stake if team_initial_stake is not None else self.initial_stake

        if progression_step >= self.max_progression_steps:
            return 0.0, True

        if cumulative_loss <= 0:
            return initial, False

        if new_odds <= 1.0:
            raise ValueError(f"Cota trebuie să fie > 1.0, primită: {new_odds}")

        stake = (cumulative_loss / (new_odds - 1)) + initial

        stake = round(stake, 2)

        return stake, False

    def calculate_potential_profit(self, stake: float, odds: float) -> float:
        """
        Calculează profitul potențial pentru un pariu.

        Args:
            stake: Miza plasată
            odds: Cota

        Returns:
            float: Profitul potențial (fără miza)
        """
        if odds <= 1.0:
            raise ValueError(f"Cota trebuie să fie > 1.0, primită: {odds}")

        profit = stake * (odds - 1)
        return round(profit, 2)

    def process_win(
        self,
        stake: float,
        odds: float
    ) -> Tuple[float, float, int]:
        """
        Procesează un pariu câștigat.

        Args:
            stake: Miza plasată
            odds: Cota la care s-a pariat

        Returns:
            Tuple[float, float, int]: (profit, new_cumulative_loss, new_progression_step)
        """
        profit = self.calculate_potential_profit(stake, odds)
        new_cumulative_loss = 0.0
        new_progression_step = 0

        return profit, new_cumulative_loss, new_progression_step

    def process_loss(
        self,
        stake: float,
        current_cumulative_loss: float,
        current_progression_step: int
    ) -> Tuple[float, float, int]:
        """
        Procesează un pariu pierdut.

        Args:
            stake: Miza pierdută
            current_cumulative_loss: Pierderea cumulată curentă
            current_progression_step: Pasul curent de progresie

        Returns:
            Tuple[float, float, int]: (loss, new_cumulative_loss, new_progression_step)
        """
        loss = -stake
        new_cumulative_loss = current_cumulative_loss + stake
        new_progression_step = current_progression_step + 1

        return loss, new_cumulative_loss, new_progression_step

    def get_progression_info(
        self,
        cumulative_loss: float,
        progression_step: int,
        next_odds: float
    ) -> dict:
        """
        Returnează informații despre starea progresiei.

        Args:
            cumulative_loss: Pierderea cumulată
            progression_step: Pasul curent
            next_odds: Cota pentru următorul meci

        Returns:
            dict: Informații despre progresie
        """
        next_stake, stop_loss_reached = self.calculate_stake(
            cumulative_loss, next_odds, progression_step
        )

        potential_profit = 0.0
        if not stop_loss_reached and next_stake > 0:
            potential_profit = self.calculate_potential_profit(next_stake, next_odds)

        return {
            "cumulative_loss": round(cumulative_loss, 2),
            "progression_step": progression_step,
            "max_progression_steps": self.max_progression_steps,
            "next_stake": next_stake,
            "next_odds": next_odds,
            "potential_profit": potential_profit,
            "stop_loss_reached": stop_loss_reached,
            "initial_stake": self.initial_stake
        }


staking_service = StakingService()
