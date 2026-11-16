package com.example.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Event
import androidx.compose.material.icons.filled.People
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.data.I18n
import com.example.model.BookingStatus
import com.example.viewmodel.GloviUiState
import com.example.viewmodel.GloviViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BookingsScreen(
    state: GloviUiState,
    viewModel: GloviViewModel,
    modifier: Modifier = Modifier
) {
    val lang = state.profile.language
    var selectedServiceId by remember { mutableStateOf(state.services.firstOrNull()?.id ?: "") }

    LaunchedEffect(state.services) {
        if (selectedServiceId.isEmpty() && state.services.isNotEmpty()) {
            selectedServiceId = state.services.first().id
        }
    }

    val currentService = state.services.find { it.id == selectedServiceId } ?: state.services.firstOrNull()
    val availableSlots = state.slots.filter { it.serviceId == currentService?.id && it.available > 0 }
    var selectedSlotId by remember(selectedServiceId) { mutableStateOf(availableSlots.firstOrNull()?.id ?: "") }

    var partySize by remember { mutableIntStateOf(2) }
    var nameInput by remember { mutableStateOf("") }
    var emailInput by remember { mutableStateOf("") }
    var formError by remember { mutableStateOf<String?>(null) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp)
            .testTag("bookings_screen")
    ) {
        Text(
            text = I18n.t("bookings", lang),
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold)
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = I18n.t("bookingCardText", lang),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )

        Spacer(modifier = Modifier.height(16.dp))

        // Booking Form Card
        Card(
            modifier = Modifier
                .fillMaxWidth()
                .testTag("card_booking_form"),
            shape = RoundedCornerShape(16.dp),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "Nueva Solicitud",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Service Selector
                Text(text = I18n.t("service", lang), style = MaterialTheme.typography.labelMedium)
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    state.services.forEach { s ->
                        FilterChip(
                            selected = s.id == selectedServiceId,
                            onClick = {
                                selectedServiceId = s.id
                                selectedSlotId = ""
                            },
                            label = { Text(s.name, maxLines = 1) },
                            modifier = Modifier
                                .weight(1f)
                                .testTag("chip_service_${s.id}")
                        )
                    }
                }

                if (currentService?.isDemo == true) {
                    Spacer(modifier = Modifier.height(6.dp))
                    Surface(
                        color = MaterialTheme.colorScheme.secondaryContainer,
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = I18n.t("demo", lang),
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSecondaryContainer,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Slot Selector
                Text(text = I18n.t("slot", lang), style = MaterialTheme.typography.labelMedium)
                Spacer(modifier = Modifier.height(6.dp))
                if (availableSlots.isNotEmpty()) {
                    var expanded by remember { mutableStateOf(false) }
                    val currentSlot = availableSlots.find { it.id == selectedSlotId } ?: availableSlots.first()

                    ExposedDropdownMenuBox(
                        expanded = expanded,
                        onExpandedChange = { expanded = it }
                    ) {
                        OutlinedTextField(
                            value = "${currentSlot.startsAt.replace("T", " ").replace("Z", "")} · ${currentSlot.available} ${I18n.t("available", lang)}",
                            onValueChange = {},
                            readOnly = true,
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                            modifier = Modifier
                                .menuAnchor()
                                .fillMaxWidth()
                                .testTag("dropdown_slot")
                        )
                        ExposedDropdownMenu(
                            expanded = expanded,
                            onDismissRequest = { expanded = false }
                        ) {
                            availableSlots.forEach { slot ->
                                DropdownMenuItem(
                                    text = {
                                        Text("${slot.startsAt.replace("T", " ").replace("Z", "")} (${slot.available} ${I18n.t("available", lang)})")
                                    },
                                    onClick = {
                                        selectedSlotId = slot.id
                                        expanded = false
                                    }
                                )
                            }
                        }
                    }
                } else {
                    Text(
                        text = I18n.t("emptySlots", lang),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error
                    )
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Party Size Stepper
                Text(text = "${I18n.t("people", lang)}: $partySize", style = MaterialTheme.typography.labelMedium)
                Spacer(modifier = Modifier.height(6.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    FilledTonalIconButton(
                        onClick = { if (partySize > 1) partySize-- },
                        modifier = Modifier.testTag("btn_decrease_party")
                    ) {
                        Text("-", style = MaterialTheme.typography.titleLarge)
                    }
                    Text(
                        text = "$partySize",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    FilledTonalIconButton(
                        onClick = { if (partySize < 12) partySize++ },
                        modifier = Modifier.testTag("btn_increase_party")
                    ) {
                        Text("+", style = MaterialTheme.typography.titleLarge)
                    }
                }

                Spacer(modifier = Modifier.height(12.dp))

                // Name Input
                OutlinedTextField(
                    value = nameInput,
                    onValueChange = { nameInput = it; formError = null },
                    label = { Text(I18n.t("name", lang)) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("input_booking_name"),
                    singleLine = true
                )

                Spacer(modifier = Modifier.height(10.dp))

                // Email Input
                OutlinedTextField(
                    value = emailInput,
                    onValueChange = { emailInput = it; formError = null },
                    label = { Text(I18n.t("email", lang)) },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("input_booking_email"),
                    singleLine = true
                )

                if (formError != null) {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = formError!!,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.bodySmall
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                Button(
                    onClick = {
                        val trimmedName = nameInput.trim()
                        val trimmedEmail = emailInput.trim()
                        if (trimmedName.length < 2) {
                            formError = "El nombre debe tener al menos 2 caracteres."
                            return@Button
                        }
                        if (!trimmedEmail.contains("@") || !trimmedEmail.contains(".")) {
                            formError = "Introduce un correo electrónico válido."
                            return@Button
                        }
                        val slotToBook = if (selectedSlotId.isNotEmpty()) selectedSlotId else availableSlots.firstOrNull()?.id ?: ""
                        if (slotToBook.isEmpty()) {
                            formError = "Selecciona un turno válido."
                            return@Button
                        }

                        val success = viewModel.createBooking(slotToBook, partySize, trimmedName, trimmedEmail)
                        if (success) {
                            nameInput = ""
                            emailInput = ""
                            formError = null
                        } else {
                            formError = "No hay plazas suficientes en este turno."
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("btn_submit_booking"),
                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                ) {
                    Text(I18n.t("request", lang))
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Existing Bookings Section
        Text(
            text = "Mis Reservas",
            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
        )
        Spacer(modifier = Modifier.height(10.dp))

        if (state.bookings.isEmpty()) {
            Card(
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
                shape = RoundedCornerShape(12.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text = I18n.t("emptyBookings", lang),
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                state.bookings.forEach { booking ->
                    Card(
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("card_booking_${booking.id}"),
                        shape = RoundedCornerShape(14.dp),
                        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
                    ) {
                        Column(modifier = Modifier.padding(14.dp)) {
                            Row(
                                modifier = Modifier.fillMaxWidth(),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = booking.serviceName,
                                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                )
                                val (statusBg, statusText) = when (booking.status) {
                                    BookingStatus.CONFIRMED -> Pair(Color(0xFFDCFCE7), Color(0xFF166534))
                                    BookingStatus.REQUESTED -> Pair(Color(0xFFFEF3C7), Color(0xFF92400E))
                                    BookingStatus.CANCELLED -> Pair(Color(0xFFFEE2E2), Color(0xFF991B1B))
                                    BookingStatus.REJECTED -> Pair(Color(0xFFF3F4F6), Color(0xFF374151))
                                }
                                Surface(
                                    color = statusBg,
                                    shape = RoundedCornerShape(6.dp)
                                ) {
                                    Text(
                                        text = I18n.t(booking.status.code, lang),
                                        color = statusText,
                                        style = MaterialTheme.typography.labelSmall,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                                    )
                                }
                            }

                            Spacer(modifier = Modifier.height(6.dp))
                            Text(
                                text = "${booking.startsAt.replace("T", " ").replace("Z", "")} · ${booking.partySize} ${I18n.t("people", lang)}",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
                            )
                            Text(
                                text = "Titular: ${booking.name} (${booking.contact})",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                            )

                            if (booking.status == BookingStatus.REQUESTED || booking.status == BookingStatus.CONFIRMED) {
                                Spacer(modifier = Modifier.height(10.dp))
                                OutlinedButton(
                                    onClick = { viewModel.cancelBooking(booking.id) },
                                    colors = ButtonDefaults.outlinedButtonColors(
                                        contentColor = MaterialTheme.colorScheme.error
                                    ),
                                    modifier = Modifier.testTag("btn_cancel_booking_${booking.id}")
                                ) {
                                    Text(I18n.t("cancel", lang))
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
