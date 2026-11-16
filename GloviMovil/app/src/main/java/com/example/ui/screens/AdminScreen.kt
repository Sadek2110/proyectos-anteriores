package com.example.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.data.I18n
import com.example.model.BookingStatus
import com.example.viewmodel.GloviUiState
import com.example.viewmodel.GloviViewModel

@Composable
fun AdminScreen(
    state: GloviUiState,
    viewModel: GloviViewModel,
    modifier: Modifier = Modifier
) {
    val lang = state.profile.language
    var tokenInput by remember { mutableStateOf("") }

    // New service form fields
    var newServiceName by remember { mutableStateOf("") }
    var newServiceDesc by remember { mutableStateOf("") }
    var newServiceKind by remember { mutableStateOf("restaurant") }
    var newServiceDemo by remember { mutableStateOf(true) }

    // New slot form fields
    var selectedServiceForSlot by remember { mutableStateOf(state.services.firstOrNull()?.id ?: "") }
    var slotDateTime by remember { mutableStateOf("2026-10-15T19:00:00Z") }
    var slotCapacity by remember { mutableIntStateOf(8) }

    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(20.dp)
            .testTag("admin_screen")
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "Operación del piloto",
                    style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold)
                )
                Text(
                    text = "Panel de control administrativo",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                )
            }

            if (state.adminAuthenticated) {
                TextButton(
                    onClick = { viewModel.adminLogout() },
                    modifier = Modifier.testTag("btn_admin_logout")
                ) {
                    Text("Cerrar sesión")
                }
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        if (!state.adminAuthenticated) {
            // Login card
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .testTag("card_admin_login"),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Acceso restringido",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "Introduce el token de administración para acceder.",
                        style = MaterialTheme.typography.bodySmall
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedTextField(
                        value = tokenInput,
                        onValueChange = { tokenInput = it },
                        label = { Text("Token de administrador") },
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("input_admin_token"),
                        singleLine = true
                    )
                    Spacer(modifier = Modifier.height(14.dp))
                    Button(
                        onClick = {
                            viewModel.adminLogin(tokenInput.ifEmpty { "admin" })
                            tokenInput = ""
                        },
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("btn_admin_login")
                    ) {
                        Text("Acceder al panel")
                    }
                }
            }
        } else {
            // Admin Dashboard
            Text(
                text = "Solicitudes de reserva (${state.bookings.size})",
                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
            )
            Spacer(modifier = Modifier.height(10.dp))

            if (state.bookings.isEmpty()) {
                Text(
                    text = "No hay solicitudes de reserva pendientes.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
                )
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    state.bookings.forEach { b ->
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .testTag("card_admin_booking_${b.id}"),
                            shape = RoundedCornerShape(14.dp),
                            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
                        ) {
                            Column(modifier = Modifier.padding(14.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Text(
                                        text = b.serviceName,
                                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                    )
                                    Surface(
                                        color = when (b.status) {
                                            BookingStatus.CONFIRMED -> Color(0xFFDCFCE7)
                                            BookingStatus.REQUESTED -> Color(0xFFFEF3C7)
                                            BookingStatus.CANCELLED -> Color(0xFFFEE2E2)
                                            BookingStatus.REJECTED -> Color(0xFFF3F4F6)
                                        },
                                        shape = RoundedCornerShape(6.dp)
                                    ) {
                                        Text(
                                            text = I18n.t(b.status.code, lang),
                                            style = MaterialTheme.typography.labelSmall,
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "${b.name} (${b.contact}) · ${b.partySize} personas",
                                    style = MaterialTheme.typography.bodySmall
                                )
                                Text(
                                    text = "Turno: ${b.startsAt.replace("T", " ").replace("Z", "")}",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
                                )

                                if (b.status == BookingStatus.REQUESTED) {
                                    Spacer(modifier = Modifier.height(10.dp))
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        Button(
                                            onClick = { viewModel.updateBookingStatus(b.id, BookingStatus.CONFIRMED) },
                                            colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary),
                                            modifier = Modifier.testTag("btn_confirm_${b.id}")
                                        ) {
                                            Text("Confirmar")
                                        }
                                        OutlinedButton(
                                            onClick = { viewModel.updateBookingStatus(b.id, BookingStatus.REJECTED) },
                                            modifier = Modifier.testTag("btn_reject_${b.id}")
                                        ) {
                                            Text("Rechazar")
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(24.dp))

            // Add Service Form
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Crear nuevo servicio",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedTextField(
                        value = newServiceName,
                        onValueChange = { newServiceName = it },
                        label = { Text("Nombre del servicio") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = newServiceDesc,
                        onValueChange = { newServiceDesc = it },
                        label = { Text("Descripción") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Checkbox(
                            checked = newServiceDemo,
                            onCheckedChange = { newServiceDemo = it }
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Servicio de demostración", style = MaterialTheme.typography.bodySmall)
                    }
                    Spacer(modifier = Modifier.height(10.dp))
                    Button(
                        onClick = {
                            if (newServiceName.isNotBlank()) {
                                viewModel.addService(newServiceName, newServiceKind, newServiceDesc, newServiceDemo)
                                newServiceName = ""
                                newServiceDesc = ""
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Guardar servicio")
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Add Slot Form
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(
                        text = "Crear nuevo turno de reserva",
                        style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    OutlinedTextField(
                        value = slotDateTime,
                        onValueChange = { slotDateTime = it },
                        label = { Text("Fecha y Hora (ISO / Texto)") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    Spacer(modifier = Modifier.height(8.dp))
                    OutlinedTextField(
                        value = slotCapacity.toString(),
                        onValueChange = { slotCapacity = it.toIntOrNull() ?: 8 },
                        label = { Text("Aforo máximo") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    Spacer(modifier = Modifier.height(10.dp))
                    Button(
                        onClick = {
                            val serviceId = if (selectedServiceForSlot.isNotEmpty()) selectedServiceForSlot else state.services.firstOrNull()?.id ?: ""
                            if (serviceId.isNotEmpty()) {
                                viewModel.addSlot(serviceId, slotDateTime, slotCapacity)
                            }
                        },
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text("Guardar turno")
                    }
                }
            }
        }
    }
}
